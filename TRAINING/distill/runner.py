"""
Teacher runner: builds batches for a job, calls the teacher through the failover client, validates every
element, and appends results to DATA/distilled/raw/<job>.jsonl with a resumable state file.

Files per job (DATA/distilled/raw/):
  <job>.jsonl          accepted rows (one per line, validated, with spans + offsets)
  <job>.rejects.jsonl  rejected elements with the reason (for the reject-rate report)
  <job>.state.json     {"done": [batch_id, ...], "failed": {batch_id: reason}, "stats": {...}}
  usage.json           per-lane calls/tokens (+ Sarvam cost estimate)

Resume: batches whose id is in `done` are skipped, so a crash, a daily cap or Ctrl-C loses at most one batch.
Failover: handled inside backends.TeacherClient (lane rotation on 429, provider failover on caps / credits).
"""
from __future__ import annotations

import hashlib
import json
import os
import logging
import random
import time
from pathlib import Path

from ..config import (
    DISTILLED_RAW_DIR, GENERATE_ROWS_PER_BATCH, GENERATE_TOTAL_ROWS, LABEL_ROWS_PER_BATCH, PROMPT_VERSION,
    INDIC_HEAVY_MIXES, LANG_MIXES, REWIND_SEEDS_PER_REQUEST, SEED_SOURCE_CAPS, TEACHER_INPUT,
)
from .backends import BackendExhausted, BatchFailed, TeacherClient
from .prompts import generate_messages, label_messages, rewind_messages, seed_pool
from .schema import validate_many

log = logging.getLogger("distill.runner")


# --------------------------------------------------------------------------
# state
# --------------------------------------------------------------------------
_EMPTY_STATE = {"done": [], "failed": {}, "stats": {"rows": 0, "rejects": 0, "batches": 0, "tokens_in": 0, "tokens_out": 0}}
CLAIM_STALE_S = 10 * 60          # a claim older than this belongs to a closed/crashed window and is taken over (a batch takes <= 3 min)
LOCK_STALE_S = 120


class JobState:
    """Per-job append-only rows/rejects + state.json.  Safe for SEVERAL PROCESSES running the same job at once
    (e.g. `--backend sarvam` and `--backend gemini` in two windows): every batch is claimed with an atomic
    O_EXCL file before it is sent, and commits merge into the on-disk state under a lock file."""

    def __init__(self, job: str, out_dir: Path = DISTILLED_RAW_DIR):
        out_dir.mkdir(parents=True, exist_ok=True)
        self.job = job
        self.rows_path = out_dir / f"{job}.jsonl"
        self.rejects_path = out_dir / f"{job}.rejects.jsonl"
        self.state_path = out_dir / f"{job}.state.json"
        self.lock_path = out_dir / f"{job}.lock"
        self.claims_dir = out_dir / "claims" / job
        self.claims_dir.mkdir(parents=True, exist_ok=True)
        self.state = self._read_state()
        self.done: set[str] = set(self.state["done"])

    # ---- disk helpers
    def _read_state(self) -> dict:
        if self.state_path.exists():
            try:
                st = json.loads(self.state_path.read_text(encoding="utf-8"))
                st.setdefault("failed", {})
                st.setdefault("stats", dict(_EMPTY_STATE["stats"]))
                return st
            except Exception:  # noqa: BLE001
                log.warning("state file unreadable - starting fresh (%s)", self.state_path)
        return json.loads(json.dumps(_EMPTY_STATE))

    def _lock(self):
        t0 = time.time()
        while True:
            try:
                fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, str(os.getpid()).encode())
                os.close(fd)
                return
            except FileExistsError:
                try:
                    holder = self.lock_path.read_text(encoding="utf-8").strip()
                except OSError:
                    holder = "?"
                if holder in ("", str(os.getpid())):
                    # released by a mount that forbids unlink (blanked), or already held by us
                    try:
                        self.lock_path.write_text(str(os.getpid()), encoding="utf-8")
                    except OSError:
                        pass
                    return
                try:
                    stale = time.time() - self.lock_path.stat().st_mtime > LOCK_STALE_S
                except OSError:
                    stale = False
                if stale:
                    # the window that held it is gone; drop the lock, or - on mounts where unlink is
                    # forbidden - simply take it over (nobody alive is holding it after LOCK_STALE_S)
                    try:
                        self.lock_path.unlink()
                    except OSError:
                        try:
                            self.lock_path.write_text(str(os.getpid()), encoding="utf-8")
                        except OSError:
                            pass
                        log.warning("took over a stale lock (%s)", self.lock_path.name)
                        return
                    continue
                if time.time() - t0 > 60:
                    raise RuntimeError(f"could not acquire {self.lock_path} for 60 s - delete it if no other run is active")
                time.sleep(0.2)

    def _unlock(self) -> None:
        try:
            self.lock_path.unlink()
        except OSError:
            try:                                   # mounts that forbid unlink: blank it = free
                self.lock_path.write_text("", encoding="utf-8")
            except OSError:
                pass

    def _claim_path(self, batch_id: str) -> Path:
        return self.claims_dir / (hashlib.sha1(batch_id.encode("utf-8")).hexdigest()[:20] + ".claim")

    # ---- API used by run_job
    def is_done(self, batch_id: str) -> bool:
        return batch_id in self.done

    def claim(self, batch_id: str) -> bool:
        """True if this process may run the batch (not done anywhere, not being run by a live process)."""
        self._lock()
        try:
            self.state = self._read_state()
            self.done = set(self.state["done"])
            if batch_id in self.done:
                return False
            cp = self._claim_path(batch_id)
            if cp.exists() and cp.stat().st_size > 0 and time.time() - cp.stat().st_mtime < CLAIM_STALE_S:
                return False
            cp.write_text(f"{os.getpid()} {time.time():.0f} {batch_id}", encoding="utf-8")
            return True
        finally:
            self._unlock()

    def release(self, batch_id: str) -> None:
        cp = self._claim_path(batch_id)
        try:
            cp.unlink()
        except OSError:
            try:                                   # mounts that forbid unlink: an empty claim file = free
                cp.write_text("", encoding="utf-8")
            except OSError:
                pass

    def commit(self, batch_id: str, rows: list[dict], rejects: list[dict], meta: dict) -> None:
        self._lock()
        try:
            with open(self.rows_path, "a", encoding="utf-8") as fh:
                fh.write("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
            with open(self.rejects_path, "a", encoding="utf-8") as fh:
                fh.write("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rejects))
            st_all = self._read_state()                       # merge with what other processes wrote meanwhile
            done = set(st_all["done"])
            done.add(batch_id)
            st_all["done"] = sorted(done)
            st_all["failed"].pop(batch_id, None)
            st = st_all["stats"]
            st["rows"] += len(rows)
            st["rejects"] += len(rejects)
            st["batches"] += 1
            st["tokens_in"] += meta.get("tokens_in", 0)
            st["tokens_out"] += meta.get("tokens_out", 0)
            st.setdefault("by_lane", {})
            st["by_lane"][meta.get("lane", "?")] = st["by_lane"].get(meta.get("lane", "?"), 0) + 1
            self.state, self.done = st_all, done
            self._save()
        finally:
            self._unlock()
        self.release(batch_id)

    def fail(self, batch_id: str, reason: str) -> None:
        self._lock()
        try:
            st_all = self._read_state()
            st_all["failed"][batch_id] = reason[:300]
            self.state, self.done = st_all, set(st_all["done"])
            self._save()
        finally:
            self._unlock()
        self.release(batch_id)

    def _save(self) -> None:
        tmp = self.state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.state, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.state_path)


# --------------------------------------------------------------------------
# batch builders
# --------------------------------------------------------------------------
def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        raise SystemExit(f"missing {path} - run `python -m CLEANING.run_pipeline` first")
    with open(path, "r", encoding="utf-8") as fh:
        return [json.loads(ln) for ln in fh if ln.strip()]


def generate_batches(total_rows: int, rows_per_batch: int, seed: int = 7) -> list[dict]:
    pool = seed_pool()
    rng = random.Random(seed)
    n_batches = max(1, -(-total_rows // rows_per_batch))
    out = []
    for i in range(n_batches):
        seeds = rng.sample(pool, k=min(4, len(pool))) if pool else []
        out.append({"batch_id": f"gen_{i:04d}", "index": i, "n": rows_per_batch, "seed_texts": seeds})
    # Devanagari / Assamese-heavy batches first: the first lane in the generate chain is Sarvam (Indic-tuned, small
    # rupee budget) - spend it where it matters, the plain Hinglish/English mixes fall through to Gemini
    out.sort(key=lambda b: (0 if b["index"] % len(LANG_MIXES) in INDIC_HEAVY_MIXES else 1, b["index"]))
    return out


def _apply_source_caps(rows: list[dict]) -> list[dict]:
    """Keep at most SEED_SOURCE_CAPS[source] rows per source (shortest texts first, so long bulletins drop out)."""
    kept, seen = [], {}
    for r in sorted(rows, key=lambda r: (r["source"], len(r.get("text") or ""), r["input_id"])):
        cap = SEED_SOURCE_CAPS.get(r["source"])
        if cap is not None and seen.get(r["source"], 0) >= cap:
            continue
        seen[r["source"]] = seen.get(r["source"], 0) + 1
        kept.append(r)
    return kept


def rewind_batches(seeds_per_request: int, source_filter: str | None = None, limit: int | None = None) -> list[dict]:
    rows = [r for r in _read_jsonl(TEACHER_INPUT) if r.get("teacher_prompt") == "rewind"]
    if source_filter:
        rows = [r for r in rows if source_filter in r["source"]]
    rows = _apply_source_caps(rows)
    # Indian / onshore / drilling seeds first - they matter most for OIL
    def prio(r: dict) -> tuple:
        m = r.get("meta") or {}
        return (0 if r["source"].startswith("alert_oisd") else 1,
                0 if (m.get("country") or "").lower() == "india" else 1,
                0 if m.get("onshore_offshore") == "onshore" else 1,
                0 if r["source"].startswith("alert_iadc") else 1, r["input_id"])
    rows.sort(key=prio)
    if limit:
        rows = rows[:limit]
    out = []
    for i in range(0, len(rows), seeds_per_request):
        chunk = rows[i:i + seeds_per_request]
        out.append({"batch_id": "rew_" + "+".join(r["input_id"] for r in chunk), "records": chunk})
    return out


def label_batches(rows_per_batch: int, source_filter: str | None = None, limit: int | None = None) -> list[dict]:
    rows = [r for r in _read_jsonl(TEACHER_INPUT) if r.get("teacher_prompt") == "label"]
    if source_filter:
        rows = [r for r in rows if source_filter in r["source"]]
    rows = _apply_source_caps(rows)
    rows.sort(key=lambda r: (0 if r["source"] == "osha_sir" else 1, r["input_id"]))   # oil & gas SIR rows before mining
    if limit:
        rows = rows[:limit]
    out = []
    for i in range(0, len(rows), rows_per_batch):
        chunk = rows[i:i + rows_per_batch]
        out.append({"batch_id": f"lab_{i // rows_per_batch:04d}_{chunk[0]['input_id']}", "rows": chunk})
    return out


def agree_batches(rows_per_batch: int, sample: int = 500, seed: int = 11) -> list[dict]:
    """Second-teacher pass: re-label a sample of ACCEPTED rows (from generate/rewind) with the §3 prompt."""
    pool = []
    for job in ("generate", "rewind"):
        p = DISTILLED_RAW_DIR / f"{job}.jsonl"
        if p.exists():
            with open(p, "r", encoding="utf-8") as fh:
                pool += [json.loads(ln) for ln in fh if ln.strip()]
    if not pool:
        raise SystemExit("nothing accepted yet - run generate/rewind first")
    rng = random.Random(seed)
    rng.shuffle(pool)
    pool = pool[:sample]
    rows = [{"input_id": r.get("id") or f"{r['batch_id']}:{r.get('batch_pos', 0)}", "text": r["text"], "source": "agree",
             "orig_verdict": r["verdict"], "orig_teacher": r["teacher"], "orig_spans": [(s["role"], s["text"]) for s in r["spans"]]} for r in pool]
    out = []
    for i in range(0, len(rows), rows_per_batch):
        chunk = rows[i:i + rows_per_batch]
        out.append({"batch_id": f"agr_{i // rows_per_batch:04d}", "rows": chunk})
    return out


def agreement_report() -> dict:
    """Compare agree.jsonl (second teacher) with the original verdicts -> DATA/distilled/raw/agreement.json"""
    p = DISTILLED_RAW_DIR / "agree.jsonl"
    if not p.exists():
        return {}
    rows = [json.loads(ln) for ln in open(p, "r", encoding="utf-8") if ln.strip()]
    n = len(rows)
    same_v = sum(1 for r in rows if r.get("orig_verdict") == r["verdict"])
    group = lambda v: "SIF" if v in ("P_SIF", "EXPOSURE", "H_SIF", "L_SIF", "CAPACITY") else ("NO" if v in ("LOW_ENERGY", "NON_EVENT", "SUCCESS") else "UNC")
    same_g = sum(1 for r in rows if group(r.get("orig_verdict")) == group(r["verdict"]))
    span_overlap = []
    for r in rows:
        a = {(role, t.lower()) for role, t in (r.get("orig_spans") or [])}
        b = {(s["role"], s["text"].lower()) for s in r["spans"]}
        if a or b:
            span_overlap.append(len(a & b) / max(1, len(a | b)))
    rep = {"rows": n, "verdict_agreement": round(same_v / max(1, n), 3), "sif_group_agreement": round(same_g / max(1, n), 3),
           "mean_span_jaccard": round(sum(span_overlap) / max(1, len(span_overlap)), 3),
           "by_orig_teacher": {}}
    for t in {r.get("orig_teacher") for r in rows}:
        sub = [r for r in rows if r.get("orig_teacher") == t]
        rep["by_orig_teacher"][t] = round(sum(1 for r in sub if r.get("orig_verdict") == r["verdict"]) / max(1, len(sub)), 3)
    (DISTILLED_RAW_DIR / "agreement.json").write_text(json.dumps(rep, indent=2), encoding="utf-8")
    log.info("agreement: %s", rep)
    return rep


# --------------------------------------------------------------------------
# execution
# --------------------------------------------------------------------------
def run_job(job: str, *, backend: str | None = None, limit: int | None = None, dry_run: bool = False,
            source_filter: str | None = None, total_rows: int | None = None, reverse: bool = False) -> dict:
    client = None if dry_run else TeacherClient(job, only_backend=backend)
    lane = None if dry_run else client.active_lane
    rows_per_batch = (lane.rows_per_batch if lane else GENERATE_ROWS_PER_BATCH)
    seeds_per_req = (lane.seeds_per_request if lane else REWIND_SEEDS_PER_REQUEST)

    if job == "generate":
        batches = generate_batches(total_rows or GENERATE_TOTAL_ROWS, min(rows_per_batch, GENERATE_ROWS_PER_BATCH))
    elif job == "rewind":
        batches = rewind_batches(min(seeds_per_req, REWIND_SEEDS_PER_REQUEST), source_filter, limit)
    elif job == "label":
        batches = label_batches(min(rows_per_batch, LABEL_ROWS_PER_BATCH), source_filter, limit)
    elif job == "agree":
        batches = agree_batches(min(rows_per_batch, LABEL_ROWS_PER_BATCH), sample=limit or 500)
    else:
        raise SystemExit(f"unknown job {job}")
    if limit and job == "generate":
        batches = batches[:limit]

    if reverse:
        batches = list(reversed(batches))       # a second window on the same job starts from the other end of the list
    state = JobState(job)
    todo = [b for b in batches if not state.is_done(b["batch_id"])]
    log.info("%s: %d batches total, %d done, %d to do%s", job, len(batches), len(batches) - len(todo), len(todo), " (reverse order)" if reverse else "")
    if dry_run:
        for b in todo[:3]:
            msgs = _messages(job, b)
            log.info("DRY RUN %s: system %d chars, user %d chars", b["batch_id"], len(msgs[0]["content"]), len(msgs[1]["content"]))
        return {"batches": len(batches), "todo": len(todo), "dry_run": True}

    t0 = time.time()
    n_ok = n_rej = 0
    net_fail = 0
    stopped = False
    skipped: list[dict] = []
    queue = list(todo)
    rounds = 0
    i = 0
    while queue:
        b = queue.pop(0)
        i += 1
        if not state.claim(b["batch_id"]):          # done or being run by another window
            if not state.is_done(b["batch_id"]):
                skipped.append(b)
            if not queue and skipped and rounds < 6 and not stopped:
                # batches held by another window (or a closed one whose claim has not expired yet): wait and retry
                rounds += 1
                log.info("%d batch(es) claimed by other windows - waiting 2 min before retrying them (round %d)", len(skipped), rounds)
                time.sleep(120)
                queue, skipped = skipped, []
            continue
        msgs = _messages(job, b)
        try:
            parsed, meta = client.chat(msgs, temperature=0.8 if job == "generate" else 0.4, expect="array")
        except BackendExhausted as exc:
            log.error("stopping: %s", exc)
            state.release(b["batch_id"])            # not a failure of the batch - another window / tomorrow can take it
            stopped = True
            break
        except BatchFailed as exc:
            if "transient errors on every lane" in str(exc):
                net_fail += 1
                state.release(b["batch_id"])        # network problem, not a bad batch - leave it for the next run
                log.warning("batch %s: could not reach the provider (%s)", b["batch_id"], str(exc)[-160:])
                if net_fail >= 3:
                    log.error("3 batches in a row could not reach the provider - check the internet connection / "
                              "provider status, then re-run the same command (it resumes).")
                    stopped = True
                    break
                continue
            log.warning("batch %s failed: %s", b["batch_id"], exc)
            state.fail(b["batch_id"], str(exc))
            continue
        net_fail = 0
        rows, rejects = _validate(job, b, parsed, meta)
        state.commit(b["batch_id"], rows, rejects, meta)
        n_ok += len(rows)
        n_rej += len(rejects)
        rate = (n_rej / max(1, n_ok + n_rej)) * 100
        log.info("[%d/%d] %s via %s: +%d rows, %d rejected (reject rate %.0f%%, %.0f rows/min)",
                 i, len(todo), b["batch_id"], meta["lane"], len(rows), len(rejects), rate, 60 * n_ok / max(1, time.time() - t0))
        if n_ok + n_rej >= 60 and rate > 60:
            log.error("reject rate above 60%% after %d rows - stopping so you can inspect %s", n_ok + n_rej, state.rejects_path)
            break
    if job == "agree":
        agreement_report()
    summary = {"job": job, "accepted_rows_this_run": n_ok, "rejected_this_run": n_rej,
               "state": state.state["stats"], "usage": client.usage_summary(), "prompt_version": PROMPT_VERSION}
    log.info("done: %s", json.dumps(summary, ensure_ascii=False)[:800])
    return summary


def _messages(job: str, b: dict) -> list[dict]:
    if job == "generate":
        return generate_messages(b["n"], b["index"], b["seed_texts"], verdict_plan=b.get("verdict_plan"))
    if job == "rewind":
        return rewind_messages(b["records"])
    return label_messages(b["rows"])          # label + agree


def _validate(job: str, b: dict, parsed, meta: dict) -> tuple[list[dict], list[dict]]:
    common = {"teacher": meta["backend"], "model": meta["model"], "batch_id": b["batch_id"]}
    if job == "rewind":
        rows, rejects = [], []
        items = parsed if isinstance(parsed, list) else [parsed]
        by_source = {r["input_id"]: r for r in b["records"]}
        for item in items:
            if not isinstance(item, dict):
                continue
            sid = item.get("source_id") or (b["records"][0]["input_id"] if len(b["records"]) == 1 else None)
            src = by_source.get(sid)
            if src is None:
                # some teachers drop the wrapper and return rows directly
                if "text" in item and len(b["records"]) == 1:
                    src, sid = b["records"][0], b["records"][0]["input_id"]
                    item = {"rows": [item]}
                else:
                    rejects.append({"problems": [f"unknown source_id {sid!r}"], **common})
                    continue
            rows_in = item.get("rows") or []
            for el in rows_in:
                # the ORIGINAL narrative is the incident being reported, not a reference to an earlier one:
                # teachers tend to mark it 'historical' (past tense), which would force NON_EVENT and reject it
                if isinstance(el, dict) and (el.get("meta") or {}).get("trap") == "original":
                    for ev in el.get("events") or []:
                        if isinstance(ev, dict) and ev.get("statement_type") == "historical":
                            ev["statement_type"] = "observed"
            ok, bad = validate_many(rows_in, source=f"rewind:{src['source']}", seed_id=sid, input_id=sid, **common)
            for r in ok:
                r["seed_lsr"] = src.get("life_saving_rules") or []
                r["seed_record_type"] = src.get("record_type")
            rows += ok
            rejects += bad
        return rows, rejects
    if job in ("label", "agree"):
        ok, bad = validate_many(parsed, source=job, **common)
        by_id = {r["input_id"]: r for r in b["rows"]}
        keep = []
        for r in ok:
            # match the annotated element back to its input row by input_id or by text
            iid = r.get("input_id")
            cand = None
            for el_id, src in by_id.items():
                if src["text"].strip() == r["text"].strip():
                    cand = src
                    break
            if cand is None and iid in by_id:
                cand = by_id[iid]
            if cand is None:
                bad.append({"problems": ["annotated text matches no input row (teacher rewrote it)"], "text": r["text"][:120], **common})
                continue
            r["input_id"], r["seed_id"], r["source"] = cand["input_id"], cand["input_id"], f"{job}:{cand['source']}"
            if job == "agree":
                r["orig_verdict"], r["orig_teacher"], r["orig_spans"] = cand.get("orig_verdict"), cand.get("orig_teacher"), cand.get("orig_spans")
            keep.append(r)
        return keep, bad
    ok, bad = validate_many(parsed, source="generate", **common)
    for i, r in enumerate(ok):
        r["seed_id"] = f"{b['batch_id']}:{r.get('batch_pos', i)}"
    return ok, bad
