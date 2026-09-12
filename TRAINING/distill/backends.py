"""
One chat client for every provider (OpenAI-style /chat/completions), with:

- lanes           : one per API key (SARVAM_API_1, SARVAM_API_2 ...); lanes of a provider rotate on 429
- rate limiting   : token-bucket per lane for RPM, plus a TPM estimate and an RPD counter persisted to disk
- failover        : 429 with "daily"/"quota" in the body, 402/403 (credits), or 3 consecutive 429s marks the
                    lane exhausted for the run and the next lane / next backend in the job chain is used
- retries         : 5xx and network errors back off exponentially (3 attempts) before failing the batch
- JSON extraction : strips ```json fences, tolerates leading prose, repairs trailing commas; returns parsed object
- accounting      : tokens in/out per lane -> DATA/distilled/raw/usage.json (cost estimate for Sarvam)

Nothing here is provider-SDK specific: `requests` only.
"""
from __future__ import annotations

import json
import logging
import re
import threading
import time
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import requests

from ..config import BACKENDS, DISTILLED_RAW_DIR, JOB_CHAINS, available_lanes

log = logging.getLogger("distill.backends")

USAGE_FILE = DISTILLED_RAW_DIR / "usage.json"
_PRICE_INR_PER_M = {"sarvam": (29.28, 73.2)}      # (input, output) - for the cost estimate only


class BackendExhausted(Exception):
    """Raised when every lane in the chain is exhausted for this run."""


class BatchFailed(Exception):
    """One batch could not be completed on any lane (bad JSON twice, etc.)."""


@dataclass
class Lane:
    backend: str
    lane: str
    key: str
    base_url: str
    auth: str
    model: str
    rpm: int
    tpm: int
    max_output_tokens: int
    rows_per_batch: int
    seeds_per_request: int
    supports_json_mode: bool
    rpd: int | None = None
    env_key: str = ""
    fallback_models: list[str] = field(default_factory=list)
    exhausted: bool = False
    exhausted_reason: str | None = None
    consecutive_429: int = 0
    budget_inr: float | None = None
    tpd: int | None = None
    tokens_today: int = 0
    extra_body: dict = field(default_factory=dict)      # provider-specific request fields (e.g. Sarvam reasoning_effort=None)
    timeout: int | None = None                           # per-provider HTTP read timeout (slow models need > 180 s)
    last_call: float = 0.0
    calls_today: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    rotate_models: bool = False                          # NVIDIA NIM: one quota for all models -> rotate for teacher diversity
    _model_idx: int = 0
    _rot: int = 0
    _dead_models: list = field(default_factory=list)

    @property
    def current_model(self) -> str:
        models = [m for m in [self.model] + list(self.fallback_models) if m not in self._dead_models] or [self.model]
        if self.rotate_models:
            return models[self._rot % len(models)]
        return models[min(self._model_idx, len(models) - 1)]

    def advance_rotation(self) -> None:
        if self.rotate_models:
            self._rot += 1

    def next_model(self) -> bool:
        if self.rotate_models:
            # a retired id: drop it from the rotation, continue with the rest
            self._dead_models.append(self.current_model)
            live = [m for m in [self.model] + list(self.fallback_models) if m not in self._dead_models]
            if live:
                log.warning("%s: model retired -> rotation continues over %s", self.lane, live)
                return True
            return False
        if self._model_idx < len(self.fallback_models):
            self._model_idx += 1
            log.warning("%s: switching model -> %s", self.lane, self.current_model)
            return True
        return False


class TeacherClient:
    """Routes chat requests over the lanes available for a job, with rate limiting and failover."""

    def __init__(self, job: str, chain: list[str] | None = None, only_backend: str | None = None, timeout: int = 180):
        self.job = job
        self.timeout = timeout
        chain = chain or JOB_CHAINS.get(job, list(BACKENDS))
        lanes = [Lane(**{k: v for k, v in l.items() if k in Lane.__dataclass_fields__}) for l in available_lanes()]
        if only_backend:
            lanes = [l for l in lanes if l.backend == only_backend]
            chain = [only_backend]
        self.lanes: list[Lane] = sorted(lanes, key=lambda l: chain.index(l.backend) if l.backend in chain else 99)
        self.lanes = [l for l in self.lanes if l.backend in chain]
        if not self.lanes:
            raise SystemExit(f"no API keys found for job '{job}' (chain {chain}). Fill .env - see .env.example")
        self._lock = threading.Lock()
        self._usage = self._load_usage()
        for backend in {l.backend for l in self.lanes}:
            group = [l for l in self.lanes if l.backend == backend]
            cfg = BACKENDS.get(backend, {})
            if backend == "openrouter":
                _refresh_openrouter_models(group, timeout=15)
            elif cfg.get("split_model_lanes") and cfg.get("discover_models"):
                self.lanes = _refresh_split_lanes(self.lanes, group, cfg, timeout=15)
            elif cfg.get("discover_models"):
                _refresh_models_generic(group, timeout=15)
        for l in self.lanes:
            l.calls_today = self._usage.get(l.lane, {}).get(str(date.today()), 0)
            l.tokens_today = self._usage.get(l.lane, {}).get(str(date.today()) + ":tokens", 0)
        log.info("lanes for %s: %s", job, ", ".join(f"{l.lane}({l.current_model})" for l in self.lanes))

    # ------------------------------------------------------------------ usage
    def _load_usage(self) -> dict:
        try:
            return json.loads(USAGE_FILE.read_text(encoding="utf-8")) if USAGE_FILE.exists() else {}
        except Exception:  # noqa: BLE001
            return {}

    def _save_usage(self, lane: Lane, tin: int, tout: int) -> None:
        # several jobs may run in parallel terminals (generate on Sarvam, rewind on Gemini): merge on disk,
        # touching only this lane's entry, so one process never overwrites another's counters
        on_disk = self._load_usage()
        u = on_disk.setdefault(lane.lane, {})
        today = str(date.today())
        u[today] = u.get(today, 0) + 1                       # additive: other windows use the same lane
        u[today + ":tokens"] = u.get(today + ":tokens", 0) + tin + tout
        lane.calls_today, lane.tokens_today = u[today], u[today + ":tokens"]
        u["tokens_in"] = u.get("tokens_in", 0) + tin
        u["tokens_out"] = u.get("tokens_out", 0) + tout
        price = _PRICE_INR_PER_M.get(lane.backend)
        if price:
            u["cost_inr_estimate"] = round(u["tokens_in"] / 1e6 * price[0] + u["tokens_out"] / 1e6 * price[1], 2)
        self._usage = on_disk
        USAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = USAGE_FILE.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(on_disk, indent=2), encoding="utf-8")
        tmp.replace(USAGE_FILE)

    def usage_summary(self) -> dict:
        return {l.lane: {"calls_today": l.calls_today, "tokens_in": l.tokens_in, "tokens_out": l.tokens_out,
                         "exhausted": l.exhausted, "reason": l.exhausted_reason} for l in self.lanes}

    # ------------------------------------------------------------------ lane choice
    def _pick(self) -> Lane:
        for l in self.lanes:
            if l.exhausted:
                continue
            if l.rpd and l.calls_today >= l.rpd:
                l.exhausted, l.exhausted_reason = True, f"daily cap {l.rpd} reached"
                log.warning("%s: %s", l.lane, l.exhausted_reason)
                continue
            if l.tpd and l.tokens_today >= l.tpd:
                l.exhausted, l.exhausted_reason = True, f"daily token cap {l.tpd} reached"
                log.warning("%s: %s", l.lane, l.exhausted_reason)
                continue
            spent = (self._usage.get(l.lane) or {}).get("cost_inr_estimate", 0.0)
            if l.budget_inr is not None and spent >= l.budget_inr:
                l.exhausted, l.exhausted_reason = True, f"budget Rs {l.budget_inr} reached (spent ~Rs {spent})"
                log.warning("%s: %s", l.lane, l.exhausted_reason)
                continue
            return l
        raise BackendExhausted("all lanes exhausted: " + "; ".join(f"{l.lane}: {l.exhausted_reason}" for l in self.lanes))

    def _throttle(self, lane: Lane) -> None:
        gap = 60.0 / max(1, lane.rpm)
        wait = lane.last_call + gap - time.time()
        if wait > 0:
            time.sleep(wait)
        lane.last_call = time.time()

    @property
    def active_lane(self) -> Lane:
        return self._pick()

    # ------------------------------------------------------------------ HTTP
    def _headers(self, lane: Lane) -> dict:
        h = {"Content-Type": "application/json"}
        if lane.auth == "sarvam":
            h["api-subscription-key"] = lane.key
            h["Authorization"] = f"Bearer {lane.key}"
        else:
            h["Authorization"] = f"Bearer {lane.key}"
        if lane.backend == "openrouter":
            h["HTTP-Referer"] = "https://github.com/sih26165"
            h["X-Title"] = "SIH26165 SIF distillation"
        return h

    def _post(self, lane: Lane, messages: list[dict], temperature: float, json_mode: bool, max_tokens: int | None) -> dict:
        body: dict = {"model": lane.current_model, "messages": messages, "temperature": temperature,
                      "max_tokens": min(max_tokens or lane.max_output_tokens, lane.max_output_tokens)}
        if json_mode and lane.supports_json_mode:
            body["response_format"] = {"type": "json_object"}
        if lane.extra_body:
            body.update(lane.extra_body)          # e.g. {"reasoning_effort": None} -> Sarvam 105B answers instead of thinking
        r = requests.post(f"{lane.base_url}/chat/completions", headers=self._headers(lane), json=body, timeout=lane.timeout or self.timeout)
        if r.status_code == 429:
            raise _RateLimited(r.text[:300])
        if r.status_code in (401, 402, 403):
            raise _LaneDead(f"{r.status_code}: {r.text[:200]}")
        low = r.text[:400].lower()
        if r.status_code == 404 or (r.status_code == 400 and ("model" in low and ("not found" in low or "not a valid" in low or "no endpoints" in low or "does not exist" in low))):
            # unknown / retired model id -> next model on this lane, or lane dead when none is left
            live_left = (len([m for m in [lane.model] + list(lane.fallback_models) if m not in lane._dead_models]) > 1) if lane.rotate_models \
                else (bool(lane.fallback_models) and lane._model_idx < len(lane.fallback_models))
            if live_left:
                log.warning("%s: model %s not available (%s) -> next model", lane.lane, lane.current_model, r.text[:80].replace("\n", " "))
                raise _ModelMissing(r.text[:200])
            raise _LaneDead(f"{r.status_code}: no usable model on this lane ({r.text[:120]})")
        if r.status_code >= 500:
            raise _Transient(f"{r.status_code}: {r.text[:200]}")
        r.raise_for_status()
        return r.json()

    # ------------------------------------------------------------------ public
    def chat(self, messages: list[dict], *, temperature: float = 0.7, json_mode: bool = True,
             max_tokens: int | None = None, expect: str = "any") -> tuple[object, dict]:
        """Send one request with failover. Returns (parsed_json, meta{lane, model, tokens_in, tokens_out, attempts})."""
        attempts = 0
        while True:
            lane = self._pick()
            attempts += 1
            self._throttle(lane)
            try:
                data = self._post(lane, messages, temperature, json_mode, max_tokens)
            except _RateLimited as exc:
                lane.consecutive_429 += 1
                msg = str(exc).lower()
                per_minute = any(w in msg for w in ("per minute", "perminute", "tpm", "rpm"))
                per_day = any(w in msg for w in ("per day", "perday", "daily", "tpd", "rpd", "credits", "insufficient", "exhausted"))
                generic_quota = "quota" in msg and not per_minute
                if (per_day and not per_minute) or (generic_quota and lane.consecutive_429 >= 2) or lane.consecutive_429 >= 3:
                    # Groq: "...on tokens per day (TPD): Limit 100000..." / Gemini: "quota exceeded" / OpenRouter: "credits"
                    lane.exhausted, lane.exhausted_reason = True, f"429 x{lane.consecutive_429}: {str(exc)[:80]}"
                    log.warning("%s exhausted -> failover (%s)", lane.lane, lane.exhausted_reason)
                else:
                    # per-minute limit: honour the provider's "try again in 12.5s" if present, else back off
                    m = re.search(r"try again in (\d+(?:\.\d+)?)\s*(ms|s|m)\b", msg)
                    if m:
                        val, unit = float(m.group(1)), m.group(2)
                        sleep = int(min(90, max(2, val / 1000 if unit == "ms" else val * 60 if unit == "m" else val)) + 1)
                    else:
                        sleep = min(60, 5 * 2 ** lane.consecutive_429)
                    log.warning("%s 429 (per-minute) -> sleeping %ds then rotating lane", lane.lane, sleep)
                    time.sleep(sleep)
                    self.lanes.append(self.lanes.pop(self.lanes.index(lane)))   # rotate to the back within its position
                continue
            except _LaneDead as exc:
                lane.exhausted, lane.exhausted_reason = True, str(exc)
                log.warning("%s dead: %s", lane.lane, exc)
                continue
            except _ModelMissing:
                if not lane.next_model():
                    lane.exhausted, lane.exhausted_reason = True, "model not found"
                continue
            except (_Transient, requests.RequestException) as exc:
                cause = _cause(exc)
                if attempts >= 3 * max(1, len(self.lanes)):
                    raise BatchFailed(f"transient errors on every lane: {cause}")
                sleep = min(60, 3 * 2 ** min(attempts, 4))
                log.warning("%s transient error -> retry in %ds  [%s]", lane.lane, sleep, cause)
                time.sleep(sleep)
                continue
            lane.consecutive_429 = 0
            lane.calls_today += 1
            model_used = lane.current_model
            lane.advance_rotation()
            usage = data.get("usage") or {}
            tin, tout = int(usage.get("prompt_tokens") or 0), int(usage.get("completion_tokens") or 0)
            lane.tokens_in += tin
            lane.tokens_out += tout
            with self._lock:
                self._save_usage(lane, tin, tout)
            content = _content(data)
            finish = (data.get("choices") or [{}])[0].get("finish_reason")
            parsed = extract_json(content, expect=expect)
            meta = {"lane": lane.lane, "backend": lane.backend, "model": model_used, "tokens_in": tin, "tokens_out": tout,
                    "attempts": attempts, "finish_reason": finish}
            if parsed is None and finish == "length" and expect == "array":
                parsed = salvage_array(content)      # keep the complete elements of a truncated array
                if parsed:
                    meta["truncated"] = True
                    log.warning("%s hit max_tokens - salvaged %d complete elements", lane.lane, len(parsed))
            if parsed is None and expect == "array":
                ok, bad = parse_array_lenient(content)   # unescaped quotes / stray tokens: keep the good elements
                if ok:
                    parsed = ok
                    meta["lenient"] = True
                    meta["elements_dropped"] = bad
                    log.warning("%s returned damaged JSON - lenient parse kept %d elements, dropped %d", lane.lane, len(ok), bad)
            if parsed is None:
                _dump_failure(lane, content, finish)
                # one repair attempt: ask the same lane to return only valid JSON
                repair = messages + [{"role": "assistant", "content": content[:6000]},
                                     {"role": "user", "content": "Your previous reply was not valid JSON. Reply again with ONLY the corrected JSON, no prose, no code fences."}]
                self._throttle(lane)
                try:
                    data2 = self._post(lane, repair, 0.0, json_mode, max_tokens)
                    lane.calls_today += 1
                    parsed = extract_json(_content(data2), expect=expect)
                    meta["repaired"] = True
                except Exception as exc:  # noqa: BLE001
                    log.warning("JSON repair failed on %s: %s", lane.lane, str(exc)[:80])
            if parsed is None:
                raise BatchFailed(f"invalid JSON from {lane.lane} ({meta['finish_reason']}): {content[:200]!r}")
            return parsed, meta


class _RateLimited(Exception):
    pass


class _LaneDead(Exception):
    pass


class _ModelMissing(Exception):
    pass


class _Transient(Exception):
    pass


# OpenRouter's ":free" roster changes every few weeks - the ids in config go stale and every call 404s.
# Preferred ids first (best instruction following for long JSON); anything else ":free" with a big context as fallback.
OPENROUTER_PREFERRED = [
    "inclusionai/ling-3.0-flash-sante:free", "inclusionai/ling-3.0-flash-fin:free", "dots-studio/dots-3-note-preview:free",
    "nvidia/nemotron-3.5-lightning:free", "thinkingmachines/inkling-small:free", "poolside/laguna-s-2.1:free",
    "meta-llama/llama-3.3-70b-instruct:free", "qwen/qwen3-235b-a22b:free", "google/gemma-3-27b-it:free", "sarvamai/sarvam-m:free",
    "deepseek/deepseek-chat-v3-0324:free", "mistralai/mistral-small-3.2-24b-instruct:free", "moonshotai/kimi-k2:free",
]
_OPENROUTER_TOO_SMALL = re.compile(r"\b(0\.5b|1b|1\.5b|2b|2\.6b|3b|4b)\b", re.I)


def _refresh_openrouter_models(lanes: list, timeout: int = 15) -> None:
    """Ask OpenRouter which ':free' models exist right now and point the lanes at live ids (config ids may be gone)."""
    try:
        r = requests.get("https://openrouter.ai/api/v1/models", timeout=timeout)
        r.raise_for_status()
        live = {m["id"]: m for m in (r.json().get("data") or []) if isinstance(m, dict) and str(m.get("id", "")).endswith(":free")}
    except Exception as exc:  # noqa: BLE001
        log.warning("could not list OpenRouter models (%s) - keeping the ids from config", str(exc)[:80])
        return
    if not live:
        return
    ordered = [m for m in OPENROUTER_PREFERRED if m in live]
    rest = sorted((m for m in live if m not in ordered and not _OPENROUTER_TOO_SMALL.search(m)),
                  key=lambda m: -int((live[m].get("context_length") or 0)))
    ordered += rest
    if not ordered:
        return
    for l in lanes:
        l.model, l.fallback_models, l._model_idx = ordered[0], ordered[1:6], 0
    log.info("OpenRouter free models live now: %s (using %s)", len(live), ", ".join(ordered[:4]))


def _refresh_models_generic(lanes: list, timeout: int = 15) -> None:
    """GET /models on providers whose ids rotate (NVIDIA NIM, Mistral, Cerebras): keep only the configured ids that
    still exist, in the configured order; if none exist, keep the config and let the 404 fallback sort it out."""
    if not lanes:
        return
    l0 = lanes[0]
    try:
        r = requests.get(f"{l0.base_url}/models", headers={"Authorization": f"Bearer {l0.key}"}, timeout=timeout)
        r.raise_for_status()
        live = {str(m.get("id")) for m in (r.json().get("data") or []) if isinstance(m, dict)}
    except Exception as exc:  # noqa: BLE001
        log.warning("%s: could not list models (%s) - keeping ids from config", l0.backend, str(exc)[:80])
        return
    wanted = [l0.model] + list(l0.fallback_models)
    keep = [m for m in wanted if m in live]
    if not keep:
        log.warning("%s: none of the configured models are listed (%d live) - keeping config order", l0.backend, len(live))
        return
    for l in lanes:
        l.model, l.fallback_models, l._model_idx, l._rot, l._dead_models = keep[0], keep[1:], 0, 0, []
    log.info("%s: %s over %s (%d of %d configured ids are live)", l0.backend, "rotating" if l0.rotate_models else "using", keep if l0.rotate_models else keep[0], len(keep), len(wanted))


_GEMINI_SKIP = re.compile(r"image|tts|live|audio|embed|native|thinking|exp$|robotics|computer|deep-research|veo|imagen|learnlm|gemma", re.I)


def _gemini_rank(mid: str) -> tuple:
    """Prefer newest flash, non-lite first: (version desc, non-lite first, name)."""
    m = re.search(r"gemini-(\d+(?:\.\d+)?)", mid)
    ver = float(m.group(1)) if m else 0.0
    return (-ver, "lite" in mid, mid)


def _refresh_split_lanes(all_lanes: list, group: list, cfg: dict, timeout: int = 15) -> list:
    """For providers with one lane per model (Gemini, Groq): ask /models with EACH key, drop lanes whose model that key
    cannot use, and - for Gemini - add lanes for the flash models the key does have (Gemini 3 for new accounts)."""
    out = [l for l in all_lanes if l not in group]
    by_key: dict[str, list] = {}
    for l in group:
        by_key.setdefault(l.env_key, []).append(l)
    for env_key, lanes in by_key.items():
        l0 = lanes[0]
        try:
            r = requests.get(f"{l0.base_url}/models", headers={"Authorization": f"Bearer {l0.key}"}, timeout=timeout)
            r.raise_for_status()
            live = {str(m.get("id", "")).replace("models/", "") for m in (r.json().get("data") or []) if isinstance(m, dict)}
        except Exception as exc:  # noqa: BLE001
            log.warning("%s: could not list models (%s) - keeping configured lanes", l0.lane, str(exc)[:80])
            out.extend(lanes)
            continue
        kept = [l for l in lanes if l.model in live]
        dropped = [l.model for l in lanes if l.model not in live]
        if l0.backend == "gemini":
            have = {l.model for l in kept}
            cands = sorted((m for m in live if m.startswith("gemini-") and "flash" in m and not _GEMINI_SKIP.search(m) and m not in have), key=_gemini_rank)
            limits = cfg.get("model_limits", {})
            for m in cands[: max(0, 3 - len(kept))]:
                nl = Lane(**{k: getattr(l0, k) for k in Lane.__dataclass_fields__ if not k.startswith("_")})
                nl.model, nl.fallback_models, nl.lane = m, [], f"{l0.lane.split(':')[0]}:{m}"
                nl.rpm, nl.rpd, nl.tpm = limits.get(m, {}).get("rpm", 9), limits.get(m, {}).get("rpd", 250), limits.get(m, {}).get("tpm", 240_000)
                nl.exhausted, nl.exhausted_reason, nl.consecutive_429 = False, None, 0
                kept.append(nl)
            kept.sort(key=lambda l: _gemini_rank(l.model))
        if dropped:
            log.warning("%s: models not available on this key, lanes dropped: %s", env_key, dropped)
        log.info("%s: lanes -> %s", env_key, [l.model for l in kept] or "NONE")
        out.extend(kept)
    return out


def _cause(exc: Exception) -> str:
    """Short, useful description of a network error: the innermost 'Caused by ...' part, not the URL boilerplate."""
    msg = str(exc)
    m = re.search(r"Caused by ([A-Za-z]+)\((.*)\)\)?$", msg, re.S)
    if m:
        inner = re.sub(r"<[^>]+>", "", m.group(2)).strip(" ,'\"")
        return f"{m.group(1)}: {inner[-160:]}"
    return msg[-200:]


def _content(data: dict) -> str:
    try:
        msg = data["choices"][0]["message"]
        return msg.get("content") or msg.get("reasoning_content") or ""
    except (KeyError, IndexError, TypeError):
        return json.dumps(data)[:2000]


def _dump_failure(lane, content: str, finish) -> None:
    """Keep the raw reply of an unparseable response so the prompt/model problem can be diagnosed."""
    try:
        d = USAGE_FILE.parent / "failures"
        d.mkdir(parents=True, exist_ok=True)
        name = f"{lane.lane.replace(':', '_').replace('/', '_')}_{int(time.time())}.txt"
        (d / name).write_text(f"finish_reason={finish} model={lane.current_model}\n\n{content}", encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass


_STRAY_TOKENS_RE = re.compile(r"<\|[a-z_]+\|>|<\/?s>|<eos>|<\|im_end\|>", re.I)


def _fix_inner_quotes(s: str) -> str:
    """Escape quotes that sit INSIDE JSON strings ('"rationale": "Monsoon "paani jama" aur ..."') - a quote inside a
    string is one whose next non-space char is not one of , : } ] (or end)."""
    out, in_str, i, n = [], False, 0, len(s)
    while i < n:
        ch = s[i]
        if in_str:
            if ch == "\\" and i + 1 < n:
                out.append(ch); out.append(s[i + 1]); i += 2; continue
            if ch == '"':
                j = i + 1
                while j < n and s[j] in " \t\r\n":
                    j += 1
                if j >= n or s[j] in ",:}]":
                    in_str = False
                    out.append(ch)
                else:
                    out.append('\\"')          # inner quote -> escaped
                i += 1; continue
            if ch == "\n":
                out.append("\\n"); i += 1; continue   # raw newline inside a string
            out.append(ch); i += 1; continue
        if ch == '"':
            in_str = True
        out.append(ch); i += 1
    return "".join(out)


def _split_top_level(text: str) -> list[str]:
    """Split the elements of the first top-level JSON array in `text` (quote/bracket aware, tolerant of stray text after it)."""
    start = text.find("[")
    if start < 0:
        return []
    elems, depth, in_str, esc, cur_start = [], 0, False, False, None
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                # same inner-quote heuristic as _fix_inner_quotes
                j = i + 1
                while j < len(text) and text[j] in " \t\r\n":
                    j += 1
                if j >= len(text) or text[j] in ",:}]":
                    in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch in "[{":
            depth += 1
            if depth == 2 and ch == "{":
                cur_start = i
        elif ch in "]}":
            depth -= 1
            if depth == 1 and ch == "}" and cur_start is not None:
                elems.append(text[cur_start:i + 1]); cur_start = None
            if depth == 0:
                break
    return elems


def parse_array_lenient(text: str) -> tuple[list, int]:
    """Element-by-element parse of a damaged JSON array (unescaped inner quotes, stray '<|channel_end|>' tokens,
    trailing commas, raw newlines).  Returns (elements_parsed, elements_dropped)."""
    if not text:
        return [], 0
    text = _STRAY_TOKENS_RE.sub("", text)
    cands = [m.group(1) for m in _FENCE_RE.finditer(text)] + [text]
    best: tuple[list, int] = ([], 0)
    for c in cands:
        ok, bad = [], 0
        for raw in _split_top_level(c):
            for attempt in (raw, _repair(raw), _fix_inner_quotes(raw), _repair(_fix_inner_quotes(raw))):
                try:
                    obj = json.loads(attempt)
                    if isinstance(obj, dict):
                        ok.append(obj)
                    break
                except json.JSONDecodeError:
                    continue
            else:
                bad += 1
        if len(ok) > len(best[0]):
            best = (ok, bad)
    return best


def salvage_array(text: str) -> list | None:
    """Return the complete top-level elements of a JSON array that was cut off by max_tokens."""
    if not text:
        return None
    start = text.find("[")
    if start < 0:
        return None
    depth, in_str, esc, last_end = 0, False, False, -1
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch in "[{":
            depth += 1
        elif ch in "]}":
            depth -= 1
            if depth == 1 and ch == "}":
                last_end = i
            if depth == 0:
                break
    if last_end < 0:
        return None
    try:
        out = json.loads(text[start:last_end + 1] + "]")
        return out if isinstance(out, list) and out else None
    except json.JSONDecodeError:
        return None


_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.S)


def extract_json(text: str, expect: str = "any"):
    """Parse the first JSON object/array in `text`. expect = 'array' | 'object' | 'any'."""
    if not text:
        return None
    cands = [m.group(1) for m in _FENCE_RE.finditer(text)] + [text]
    for c in cands:
        c = c.strip()
        start_chars = "[{" if expect == "any" else ("[" if expect == "array" else "{")
        idx = min([i for i in (c.find(ch) for ch in start_chars) if i >= 0] or [-1])
        if idx < 0:
            continue
        chunk = c[idx:]
        for attempt in (chunk, _repair(chunk)):
            try:
                obj = json.loads(attempt)
            except json.JSONDecodeError:
                # try trimming to the last closing bracket
                end = max(attempt.rfind("]"), attempt.rfind("}"))
                if end > 0:
                    try:
                        obj = json.loads(attempt[:end + 1])
                    except json.JSONDecodeError:
                        continue
                else:
                    continue
            if expect == "array" and isinstance(obj, dict):
                # some models wrap arrays: {"rows": [...]} / {"items": [...]}
                for v in obj.values():
                    if isinstance(v, list):
                        return v
                return [obj]
            if expect == "object" and isinstance(obj, list) and len(obj) == 1 and isinstance(obj[0], dict):
                return obj[0]
            return obj
    return None


def _repair(s: str) -> str:
    s = re.sub(r",\s*([}\]])", r"\1", s)          # trailing commas
    s = s.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    return s
