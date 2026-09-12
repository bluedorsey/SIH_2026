"""
Offline teacher lane: use a coding agent (Antigravity / Gemini, Cursor, ChatGPT, ...) as one more teacher,
without any API key, while the API windows keep running on the same job.

    python -m TRAINING.distill.offline --job rewind --next      # claim the next unfinished batch -> writes a prompt file
    python -m TRAINING.distill.offline --job rewind --submit    # validate DATA/distilled/offline/answer.json and commit it
    python -m TRAINING.distill.offline --job rewind --release   # give the claimed batch back (abandon it)
    python -m TRAINING.distill.offline --status                 # what is claimed right now

Why this exists: the agent must NOT hand-edit *.jsonl / *.state.json - those are shared with the running
API windows.  This module reuses the exact same batching, claiming, validation and commit path as
run_distill, so an offline lane behaves like any other backend (resumable, no duplicate work, same quality bar).

Files (DATA/distilled/offline/):
    current_batch.md   the prompt for the agent: system rules + the rows to annotate
    answer.json        the agent writes its JSON array here
    claimed.json       which batch_id is open, so --submit knows what it is committing
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "TRAINING.distill"  # noqa: A001

from ..config import (  # noqa: E402
    DISTILLED_RAW_DIR, GENERATE_ROWS_PER_BATCH, GENERATE_TOTAL_ROWS, LABEL_ROWS_PER_BATCH,
    PROMPT_VERSION, REWIND_SEEDS_PER_REQUEST,
)
from .backends import extract_json, parse_array_lenient  # noqa: E402
from .runner import (  # noqa: E402
    JobState, _messages, _validate, agree_batches, generate_batches, label_batches, rewind_batches,
)

log = logging.getLogger("distill.offline")

OFFLINE_DIR = DISTILLED_RAW_DIR.parent / "offline"
BATCH_FILE = OFFLINE_DIR / "current_batch.md"
ANSWER_FILE = OFFLINE_DIR / "answer.json"
CLAIM_FILE = OFFLINE_DIR / "claimed.json"


def _batches(job: str, limit: int | None = None, replan: str | None = None) -> list[dict]:
    if job == "generate":
        return generate_batches(GENERATE_TOTAL_ROWS, GENERATE_ROWS_PER_BATCH)
    if job == "rewind":
        return rewind_batches(REWIND_SEEDS_PER_REQUEST, None, limit)
    if job == "label":
        return label_batches(LABEL_ROWS_PER_BATCH, None, limit)
    if job == "agree":
        return agree_batches(LABEL_ROWS_PER_BATCH, sample=limit or 500)
    raise SystemExit(f"unknown job {job}")


def _tagged(batches: list[dict], replan: str | None) -> list[dict]:
    """Re-run the SAME seeds under a new prompt plan: a tagged batch id counts as fresh work,
    so already-done seeds can be revisited without touching the rows they produced before."""
    if not replan:
        return batches
    for b in batches:
        b["batch_id"] = f"{b['batch_id']}#{replan}"
    return batches


def _plan_generate(b: dict) -> None:
    """Point this batch at whatever the corpus is short of, recomputed each time."""
    from ..config import TARGET_TRAIN_ROWS, VERDICT_QUOTA
    have: dict[str, int] = {}
    for job in ("generate", "rewind", "label"):
        f = DISTILLED_RAW_DIR / f"{job}.jsonl"
        if not f.exists():
            continue
        with open(f, "r", encoding="utf-8") as fh:
            for ln in fh:
                if not ln.strip():
                    continue
                try:
                    v = json.loads(ln).get("verdict")
                except json.JSONDecodeError:
                    continue
                if v:
                    have[v] = have.get(v, 0) + 1
    short = sorted(((int(q * TARGET_TRAIN_ROWS) - have.get(v, 0), v) for v, q in VERDICT_QUOTA.items()),
                   reverse=True)
    short = [(d, v) for d, v in short if d > 0][:3]
    if not short:
        return
    total = sum(d for d, _ in short)
    n = b["n"]
    plan: list[str] = []
    for i, (d, v) in enumerate(short):
        k = n - len(plan) if i == len(short) - 1 else max(1, round(n * d / total))
        plan += [v] * k
    b["verdict_plan"] = plan[:n]
    log.info("verdict plan for this batch: %s", {v: plan.count(v) for v in dict.fromkeys(plan)})


def _merge(job: str, batches: list[dict]) -> dict:
    """Fuse several claimed batches into one prompt so a single request covers more seeds.
    The underlying batch ids never change, so the API windows still see the same units and
    the claim system still prevents duplicate work."""
    if len(batches) == 1:
        return batches[0]
    key = "records" if job == "rewind" else "rows"
    fused: list[dict] = []
    for b in batches:
        fused += b[key]
    return {"batch_id": "+".join(b["batch_id"] for b in batches), key: fused,
            "n": sum(b.get("n", 0) for b in batches), "index": batches[0].get("index", 0),
            "seed_texts": batches[0].get("seed_texts", [])}


def _clear(path: Path) -> None:
    """Empty a file instead of deleting it - some mounts (and the Cowork device VM) forbid unlink."""
    try:
        path.write_text("", encoding="utf-8")
    except OSError:
        pass


def _read_claim() -> dict | None:
    if not CLAIM_FILE.exists():
        return None
    try:
        raw = CLAIM_FILE.read_text(encoding="utf-8").strip()
        return json.loads(raw) if raw else None
    except Exception:  # noqa: BLE001
        return None


def cmd_next(job: str, limit: int | None, bundle: int = 1, replan: str | None = None) -> int:
    OFFLINE_DIR.mkdir(parents=True, exist_ok=True)
    open_claim = _read_claim()
    if open_claim and not open_claim.get("submitted"):
        ids = open_claim.get("batch_ids") or ([open_claim["batch_id"]] if open_claim.get("batch_id") else [])
        print(f"a batch is still open: {len(ids)} batch(es) of {open_claim.get('job')}")
        for i in ids:
            print(f"    {i}")
        print("submit it first  (--submit)  or abandon it  (--release)")
        return 2

    batches = _tagged(_batches(job, limit), replan)
    state = JobState(job)
    todo = [b for b in batches if not state.is_done(b["batch_id"])]
    if not todo:
        print(f"NO_BATCHES_LEFT: every {job} batch is done ({len(batches)} total).")
        return 0

    picked: list[dict] = []
    for b in todo:
        if len(picked) >= max(1, bundle):
            break
        if state.claim(b["batch_id"]):
            picked.append(b)
    if not picked:
        print(f"all {len(todo)} remaining {job} batches are claimed by other windows - wait a few minutes and retry")
        return 3

    if job == "generate":
        if len(picked) > 1:
            for extra in picked[1:]:
                state.release(extra["batch_id"])
            picked = picked[:1]            # generate replies cannot be split back per batch
        _plan_generate(picked[0])
    merged = _merge(job, picked)
    msgs = _messages(job, merged)
    system = msgs[0]["content"]
    user = msgs[1]["content"]
    # the rules are identical for every batch of a job -> keep them in their own file so the agent reads
    # them ONCE and every later batch costs only the rows + the answer (roughly a third of the tokens)
    rules_file = OFFLINE_DIR / f"rules_{job}.md"
    rules_text = f"<!-- {job} | {PROMPT_VERSION} -->\n{system}\n"
    fresh_rules = not rules_file.exists() or rules_file.read_text(encoding="utf-8") != rules_text
    if fresh_rules:
        rules_file.write_text(rules_text, encoding="utf-8")
    BATCH_FILE.write_text(
        f"<!-- batch {merged['batch_id']} | job {job} | {PROMPT_VERSION} -->\n"
        f"# RULES\n\nFollow `{rules_file.as_posix()}` exactly."
        + ("  **These rules CHANGED - read that file again before answering.**\n\n" if fresh_rules else
           "  You have already read it; do NOT open it again.\n\n")
        + f"# ROWS TO ANNOTATE\n\n{user}\n\n"
        f"# OUTPUT\n\nWrite ONLY the JSON array to {ANSWER_FILE.as_posix()} "
        f"- first character '[', last character ']', no markdown fences, no commentary.\n",
        encoding="utf-8",
    )
    _clear(ANSWER_FILE)
    ids = [b["batch_id"] for b in picked]
    CLAIM_FILE.write_text(json.dumps({"job": job, "batch_ids": ids, "at": time.time(),
                                      "submitted": False, "replan": replan}, indent=2), encoding="utf-8")
    remaining = len(todo) - len(ids)
    n_units = len(merged.get("records") or merged.get("rows") or [])
    print(f"BATCH_READY {len(ids)} batch(es), {n_units} seed(s) in one request  ({remaining} batches left after this)")
    print(f"read: {BATCH_FILE}")
    print(f"write your JSON array to: {ANSWER_FILE}")
    return 0


def _json_error(raw: str, path: Path) -> str:
    """Point the agent at the exact character that broke its JSON, so it can fix that one spot."""
    try:
        json.loads(raw)
        return "no error"
    except json.JSONDecodeError as e:
        lo, hi = max(0, e.pos - 200), min(len(raw), e.pos + 120)
        return (f"JSON is broken at line {e.lineno}, column {e.colno}: {e.msg}\n"
                f"--- text around the problem (the break is at the >>><<< mark) ---\n"
                f"{raw[lo:e.pos]}>>><<<{raw[e.pos:hi]}\n"
                f"--- end ---\n"
                f"Fix ONLY that spot in {path} and run --submit again. The batch is still yours; "
                f"nothing was committed.")


_MISSING_ROW_BRACE = re.compile(r"\}\]\s*\n(\s*)\]")


def _mend(raw: str):
    """Teachers often close the inner `events` array and forget the `}` of the row object.
    Repair that one shape (and a trailing comma) and keep it only if the result really parses."""
    for cand in (_MISSING_ROW_BRACE.sub(lambda m: "}]\n" + m.group(1) + "\t}\n" + m.group(1) + "]", raw),
                 re.sub(r",\s*([\]\}])", r"\1", raw)):
        if cand == raw:
            continue
        try:
            obj = json.loads(cand)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, list) and obj:
            return obj
    return None


def _load_answer(path: Path):
    if not path.exists():
        raise SystemExit(f"{path} not found - write the JSON array there first")
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        raise SystemExit(f"{path} is empty - write the JSON array there first")
    try:
        parsed = extract_json(raw, expect="array")
    except Exception:  # noqa: BLE001
        parsed = None
    if parsed:
        return parsed
    mended = _mend(raw)
    if mended is not None:
        log.warning("answer.json was missing a closing brace - repaired it automatically")
        return mended
    lenient, dropped = parse_array_lenient(raw)
    if lenient:
        # a request is expensive when the agent is rate-limited: keep the elements that DO parse
        # rather than throwing the whole reply away because of a broken tail
        log.warning("answer.json was not strict JSON - kept %d element(s), %d unreadable", len(lenient), dropped)
        return lenient
    raise SystemExit(_json_error(raw, path))


def _slice_answer(job: str, b: dict, parsed):
    """Keep only the answer elements that belong to this batch (a bundled request covers several)."""
    if not isinstance(parsed, list):
        return parsed
    if job == "generate":
        return parsed                      # nothing to split: a generate batch has no per-seed ids
    if job == "rewind":
        want = {r["input_id"] for r in b["records"]}
        sub = [it for it in parsed if isinstance(it, dict) and it.get("source_id") in want]
        return sub if sub else ([parsed[0]] if len(b["records"]) == 1 and len(parsed) == 1 else sub)
    want = {r["input_id"] for r in b["rows"]}
    texts = {(r.get("text") or "").strip() for r in b["rows"]}
    return [it for it in parsed if isinstance(it, dict)
            and (it.get("input_id") in want or (it.get("text") or "").strip() in texts)]


def cmd_submit(model_name: str, answer_path: Path, dry: bool = False) -> int:
    claim = _read_claim()
    if not claim or claim.get("submitted"):
        print("no open batch - run --next first")
        return 2
    job = claim["job"]
    ids = claim.get("batch_ids") or [claim["batch_id"]]
    known = {b["batch_id"]: b for b in _tagged(_batches(job), claim.get("replan"))}
    mine = [known[i] for i in ids if i in known]
    if not mine:
        print(f"batch(es) {ids} no longer in the batch list (config changed?) - releasing")
        for i in ids:
            JobState(job).release(i)
        _clear(CLAIM_FILE)
        return 3

    parsed = _load_answer(answer_path)
    meta = {"backend": "offline", "model": model_name, "lane": f"offline:{model_name}", "tokens_in": 0, "tokens_out": 0}
    state = JobState(job)
    tot_rows = tot_rej = 0
    shown = 0
    for b in mine:
        sub = _slice_answer(job, b, parsed)
        rows, rejects = _validate(job, b, sub, meta)
        tot_rows += len(rows)
        tot_rej += len(rejects)
        if not dry:
            state.commit(b["batch_id"], rows, rejects, meta)
        for r in rejects:
            if shown < 12:
                print("  REJECTED: " + "; ".join(r.get("problems") or [])[:220])
                shown += 1
    if dry:
        print(f"DRY RUN {len(mine)} batch(es): {tot_rows} rows would be accepted, {tot_rej} rejected (nothing written)")
        return 0
    CLAIM_FILE.write_text(json.dumps({**claim, "submitted": True}, indent=2), encoding="utf-8")
    total = state.state["stats"]["rows"]
    print(f"COMMITTED {len(mine)} batch(es): +{tot_rows} rows accepted, {tot_rej} rejected  (job total now {total})")
    if tot_rej > shown:
        print(f"  ... and {tot_rej - shown} more (see {state.rejects_path})")
    rows = [1] * tot_rows
    rejects = [1] * tot_rej
    if rows or not rejects:
        print("NEXT: run --next for the following batch.")
    else:
        print("NOTHING accepted - re-read the reject reasons above, fix answer.json and run --submit again "
              "(the batch is already committed, so fixes go into the NEXT batch instead).")
    return 0


def cmd_release() -> int:
    claim = _read_claim()
    if not claim:
        print("nothing claimed")
        return 0
    ids = claim.get("batch_ids") or ([claim["batch_id"]] if claim.get("batch_id") else [])
    st = JobState(claim["job"])
    for i in ids:
        st.release(i)
    _clear(CLAIM_FILE)
    print(f"released {len(ids)} batch(es) of {claim['job']}")
    return 0


def cmd_status() -> int:
    claim = _read_claim()
    print(json.dumps(claim or {"claimed": None}, indent=2))
    for job in ("generate", "rewind", "label", "agree"):
        p = DISTILLED_RAW_DIR / f"{job}.state.json"
        if p.exists():
            st = json.loads(p.read_text(encoding="utf-8"))
            by = st.get("stats", {}).get("by_lane", {})
            off = sum(v for k, v in by.items() if k.startswith("offline:"))
            print(f"{job:9s} rows={st['stats']['rows']:6d}  batches={st['stats']['batches']:5d}  offline_batches={off}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="offline (no-API) teacher lane driven by a coding agent")
    ap.add_argument("--job", choices=["generate", "rewind", "label", "agree"])
    ap.add_argument("--next", action="store_true", help="claim the next unfinished batch and write the prompt file")
    ap.add_argument("--submit", action="store_true", help="validate + commit the answer for the open batch")
    ap.add_argument("--dry-submit", action="store_true", help="validate the answer and show accept/reject counts WITHOUT committing")
    ap.add_argument("--release", action="store_true", help="abandon the open batch")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--answer", default=str(ANSWER_FILE), help="path of the JSON array (default DATA/distilled/offline/answer.json)")
    ap.add_argument("--model", default="antigravity-gemini", help="name recorded as the teacher for these rows")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--replan", default=None,
                    help="re-run seeds that are already done, under the current prompt (e.g. --replan v2). "
                         "Rows made earlier are kept; the tagged batch counts as new work.")
    ap.add_argument("--bundle", type=int, default=1,
                    help="how many batches to put in ONE request (default 1). Use 3-4 when the agent is "
                         "rate-limited by request count rather than tokens.")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(name)s: %(message)s")

    if a.status:
        return cmd_status()
    if a.release:
        return cmd_release()
    if a.submit or a.dry_submit:
        return cmd_submit(a.model, Path(a.answer), dry=a.dry_submit)
    if a.next:
        if not a.job:
            raise SystemExit("--next needs --job")
        return cmd_next(a.job, a.limit, a.bundle, a.replan)
    ap.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
