"""
Safety alerts (IADC / IMCA / Step Change / OISD) -> structured incident records

Input : DATA/RAW/Safety Alerts/<SOURCE>/index.jsonl  + files/*.pdf|zip   (from CLEANING/fetch/fetch_alerts.py)
        ...or just PDFs dropped manually into DATA/RAW/Safety Alerts/<SOURCE>/files/
Output: DATA/Processed/alerts/alerts.jsonl (+csv, stats.json)

For every alert
- text = PDF text when an attachment exists (pdfplumber, zip members extracted), else the HTML text
- split into narrative / what_went_wrong / corrective_actions by the headings in config.ALERT_SECTION_MAP
  ("What happened", "What caused it", "Corrective actions", "Lessons learned" ...)
- Life-Saving Rules from tags or from the text ("Life Saving Rules referenced: ...") -> canonical names
- marine-only topics (diving bell, ROV, DP, mooring, gangway ...) flagged `off_domain` so they can be
  excluded from oil & gas training while still counting for the LSR mapper
- outcome flags (fatality / injury / near miss) from the text; duplicates flagged
"""
from __future__ import annotations

import io
import json
import logging
import re
import zipfile
from pathlib import Path

from .common.dedup import mark_duplicates
from .common.io import write_csv, write_json, write_jsonl
from .common.lsr import canonical_lsr_list
from .common.text import clean_text, reflow_pdf_lines, sha1, word_count
from .config import ALERT_DROP_TOPICS_RE, ALERT_MAX_PDF_PAGES, ALERT_SECTION_MAP, ALERT_SOURCES, MIN_TEXT_CHARS, OUT_ALERTS_DIR, RAW_ALERTS_DIR

log = logging.getLogger("clean.alerts")

_HEADING_RE = re.compile(
    r"^\s*(?:#+\s*)?(" + "|".join(re.escape(k) for k in sorted(ALERT_SECTION_MAP, key=len, reverse=True)) + r")\s*[:?]?\s*$",
    re.I | re.M,
)
_LSR_LINE_RE = re.compile(r"life[- ]saving rules?\s*(?:referenced|:)?\s*[:\-]?\s*(.+)", re.I)
_FATAL_RE = re.compile(r"\b(fatal(?:ity|ities|ly)?|died|death|was killed|were killed|deceased)\b", re.I)
_INJ_RE = re.compile(r"\b(injur(?:y|ies|ed)|fractur|amputat|burn(?:s|ed)?|laceration|hospital|lti\b|medical treatment|first aid)\b", re.I)
_NM_RE = re.compile(r"\b(near[- ]miss|near[- ]hit|no injur|no one was (?:hurt|injured)|nobody was (?:hurt|injured)|high potential|hipo)\b", re.I)
_OFF_DOMAIN = re.compile(ALERT_DROP_TOPICS_RE, re.I)
# "could have resulted in a fatality" is potential, not actual
_HEDGE_BEFORE_RE = re.compile(
    r"\b(could|might|may|would|can|potential(?:ly)?|possibl[ey]|worst[- ]case|risk of|likely|narrowly|avoided|prevented|"
    r"averted|no|without|zero|near)\b[^.]{0,60}$", re.I)
_POTENTIAL_SENT_RE = re.compile(
    r"[^.!?\n]*\b(could have|might have|may have|would have|potential(?:ly)?|worst[- ]case|had the potential|could easily)\b[^.!?\n]*[.!?]?", re.I)
# IADC / IMCA title outcome codes  ->  canonical actual_outcome
_OUTCOME_PATTERNS = [
    ("fatality", r"\bfatal(?:ity|ities)?\b"),
    ("lost_time_injury", r"\b(?:lti|ltis|dafwc|lost[- ]time(?: injur(?:y|ies)| incident)?|lost workday)\b"),
    ("restricted_work", r"\b(?:rwc|rwdc|rwi|restricted work(?: case| injury| duty)?)\b"),
    ("medical_treatment", r"\b(?:mto|mtc|mti|medical treatment(?: only| case| injury)?)\b"),
    ("first_aid", r"\bfirst[- ]aid(?: case| injury| only)?\b"),
    ("near_miss", r"\b(?:near[- ]miss|near[- ]hit|high potential|hipo)\b"),
    ("equipment_damage", r"\b(?:equipment|property|asset) damage\b|\bdropped object\b(?! injur)"),
]
_OUTCOME_RES = [(k, re.compile(rx, re.I)) for k, rx in _OUTCOME_PATTERNS]
_IADC_REF_RE = re.compile(r"\b(?:safety\s+)?alert\s*(?:no\.?|#)?\s*(\d{1,2})\s*[-\u2013\u2014]\s*(\d{2,3})\b", re.I)
_IADC_TITLE_REF_RE = re.compile(r"^\s*(\d{2})\s*[-\u2013\u2014]\s*(\d{2,3})\b")
_CONSEQ_WORD_RE = re.compile(r"\b(fatal|death|die|kill|injur|serious|severe|major|life|harm|hospital|amputat|fractur|burn|crush|struck|dropped|fall|fell|"
                             r"explos|fire|electrocut|drown|collapse|loss of|catastroph|disab)\w*", re.I)
_BOILERPLATE_RES = [re.compile(rx, re.I) for rx in (
    r"to address this incident,?\s+this company issued the following(?: to (?:rig|its) personnel)?\s*:?",
    r"the corrective actions? stated in this alert are one company'?s attempts? to address the incident,? and do not necessarily reflect the position of iadc or the iadc hse committee\.?",
    r"iadc safety alert\s*",
    r"the following is a\s+(?:safety\s+)?alert issued by [^.\n]*\.",
    r"(?:please|kindly) (?:forward|circulate|distribute|share) (?:this|the) (?:alert|information)[^.\n]*\.",
    r"this (?:safety )?(?:alert|flash) is (?:issued|provided|intended) (?:for|as) (?:information|awareness)[^.\n]*\.",
    r"members are (?:reminded|encouraged)[^.\n]*\.",
    r"provided for information purposes? only\.?\s*this information should be evaluated to determine if it is applicable in your\s*operations,?\s*to avoid recurrence of such incidents\.?",
    r"^\s*page\s+\d+(?:\s+of\s+\d+)?\s*$",
)]
_BOILERPLATE_RES = [re.compile(rx.pattern, re.I | re.M) for rx in _BOILERPLATE_RES]
MARINE_SOURCES = {"IMCA", "StepChange"}      # only marine bulletins get the off-domain topic filter
_DEVANAGARI_RE = re.compile("[\u0900-\u097f]")
_LANG_STOPWORDS = {
    "en": {"the", "and", "was", "were", "with", "that", "this", "for", "from", "which", "had", "been", "not", "while", "during", "into"},
    "es": {"el", "la", "los", "las", "del", "que", "una", "por", "para", "con", "fue", "estaba", "se", "al", "como"},
    "pt": {"o", "os", "da", "do", "das", "dos", "que", "uma", "por", "para", "com", "foi", "estava", "não", "ao"},
    "fr": {"le", "la", "les", "des", "une", "que", "pour", "avec", "dans", "sur", "était", "été", "est", "pas", "qui"},
    "id": {"yang", "dan", "di", "untuk", "dengan", "tidak", "pada", "dari", "ini", "itu", "adalah", "telah", "ke", "oleh"},
    "ru": set(),
}
_LANG_FILE_HINT_RE = re.compile(r"(?:[_\-. (]|^)(spanish|espanol|español|portuguese|portugues|português|french|francais|français|bahasa|indonesian|hindi|russian|arabic|chinese|thai|vietnamese)(?:[_\-. )]|$)", re.I)


_OISD_REF_RE = re.compile(r"OISD\s*/\s*SA\s*/\s*(\d{4}-\d{2})\s*/\s*([A-Z&]+)\s*/\s*(\d{1,3})", re.I)
_OISD_DATE_RE = re.compile(r"\b(?:dated?|dt)\s*[.:]*\s*(\d{1,2})[./-](\d{1,2})[./-](\d{4})", re.I)
_OISD_FIELD_RE = re.compile(r"^\s*(title|location|activity|loss\s*/?\s*outcome|outcome)\s*:\s*(.+)$", re.I | re.M)
OISD_SEGMENTS = {"E&P": "exploration_production", "P&E": "projects_engineering", "PL": "pipelines", "MOLPG": "marketing_lpg",
                 "MOPOL": "marketing_pol", "REF": "refinery", "GP": "gas_processing", "LPG": "lpg"}


def oisd_header(text: str) -> dict:
    """Reference / date / Title / Location / Loss-Outcome block that every OISD safety alert starts with."""
    head = text[:1500]
    out: dict = {}
    m = _OISD_REF_RE.search(head)
    if m:
        seg = m.group(2).upper()
        out["reference"] = f"OISD/SA/{m.group(1)}/{seg}/{m.group(3).zfill(2)}"
        out["segment"] = OISD_SEGMENTS.get(seg, seg.lower())
        out["year"] = int(m.group(1)[:4])
    m = _OISD_DATE_RE.search(head)
    if m:
        d, mo, y = (int(x) for x in m.groups())
        out["date"] = f"{y:04d}-{mo:02d}-{d:02d}"
        out.setdefault("year", y)
    for fm in _OISD_FIELD_RE.finditer(head):
        key = fm.group(1).lower()
        val = clean_text(fm.group(2))
        if key == "title":
            out["title"] = val
        elif key == "location":
            out["location"] = val
        elif key == "activity":
            out["activity"] = val
        else:
            out["loss_outcome"] = val
    lo = (out.get("loss_outcome") or "").lower()
    if lo:
        out["actual_outcome"] = ("fatality" if re.search(r"fatal|death|died|killed", lo) else
                                 "injury" if re.search(r"injur|burn|fractur|hospital", lo) else
                                 "equipment_damage" if re.search(r"fire|loss|damage|burnt|spill|leak|explos", lo) else
                                 "near_miss" if re.search(r"no (?:injury|loss)|near miss", lo) else None)
    return out


def actual_fatality(text: str) -> bool:
    """True only when a fatality word is NOT hedged ("could have resulted in a fatality" -> False)."""
    for m in _FATAL_RE.finditer(text):
        before = text[max(0, m.start() - 80):m.start()]
        if not _HEDGE_BEFORE_RE.search(before):
            return True
    return False


def potential_consequence(text: str) -> str | None:
    """First hedged sentence that names a harm ("could have resulted in a fatality") from reflowed text."""
    flat = re.sub(r"\s*\n\s*", " ", text or "")
    for m in _POTENTIAL_SENT_RE.finditer(flat):
        sent = clean_text(m.group(0))
        if sent and _CONSEQ_WORD_RE.search(sent) and 20 <= len(sent) <= 400:
            return sent
    return None


def outcome_code(text: str) -> str | None:
    """Canonical actual outcome from a title/body snippet (first match in severity order)."""
    if not text:
        return None
    hits = []
    for name, rx in _OUTCOME_RES:
        m = rx.search(text)
        if m:
            before = text[max(0, m.start() - 80):m.start()]
            if name != "near_miss" and _HEDGE_BEFORE_RE.search(before):
                continue                       # "could have been a fatality" is not the actual outcome
            hits.append((m.start(), name))
    if not hits:
        return None
    # title order wins (an IADC title reads "... results in LTI")
    return sorted(hits)[0][1]


def _yy_to_year(yy: int) -> int:
    return 1900 + yy if yy >= 90 else 2000 + yy


def iadc_reference(text: str, title: str | None = None, date: str | None = None) -> tuple[str | None, int | None]:
    """IADC alert number normalised to 'YY-NN' + year.
    New titles read '19-04 Finger Injury ...' and the PDF says 'Alert 4-19' (NN-YY); old ones read 'ALERT 00-01' (YY-NN)."""
    m = _IADC_TITLE_REF_RE.match(title or "")
    if m:
        return f"{m.group(1)}-{m.group(2).zfill(2)}", _yy_to_year(int(m.group(1)))
    m = _IADC_REF_RE.search(text or "") or _IADC_REF_RE.search(title or "")
    if not m:
        return None, None
    a, b = m.group(1), m.group(2)
    dy = re.match(r"(\d{4})", date or "")
    if dy:
        yy = int(dy.group(1)) % 100
        if int(a) == yy:
            return f"{int(a):02d}-{b.zfill(2)}", int(dy.group(1))
        if int(b) == yy:
            return f"{int(b):02d}-{a.zfill(2)}", int(dy.group(1))
    if len(a) == 2:                                    # old style YY-NN
        return f"{a}-{b.zfill(2)}", _yy_to_year(int(a))
    return f"{b.zfill(2)}-{a.zfill(2)}", _yy_to_year(int(b))   # new style NN-YY


def strip_boilerplate(text: str) -> str:
    for rx in _BOILERPLATE_RES:
        text = rx.sub(" ", text)
    return re.sub(r"[ \t]{2,}", " ", text)


def text_language(text: str) -> str:
    """Rough script/stopword language guess for an attachment: en / hi / es / pt / fr / id / other."""
    if not text or len(text) < 40:
        return "other"
    if len(_DEVANAGARI_RE.findall(text)) > 0.15 * max(1, len(re.findall(r"\S", text))):
        return "hi"
    toks = re.findall(r"[a-záéíóúàâãçêôõñü]+", text.lower())
    if not toks:
        return "other"
    scores = {lang: sum(1 for t in toks if t in sw) / len(toks) for lang, sw in _LANG_STOPWORDS.items() if sw}
    best = max(scores, key=scores.get)
    return best if scores[best] >= 0.02 else "other"


def choose_attachment_texts(items: list[tuple[str, str]]) -> tuple[str, str | None, dict]:
    """items = [(file_name, text)]  ->  (english_text, hindi_text_or_None, info).  Non-English/Hindi translations are skipped."""
    en, hi, info = [], [], {"attachments": len(items), "languages": []}
    for fname, txt in items:
        if not txt or not txt.strip():
            continue
        hint = _LANG_FILE_HINT_RE.search(fname or "")
        lang = text_language(txt)
        if hint and lang == "other":
            lang = {"hindi": "hi"}.get(hint.group(1).lower(), "other")
        info["languages"].append({"file": fname, "lang": lang, "chars": len(txt)})
        if lang == "en":
            en.append(txt)
        elif lang == "hi":
            hi.append(txt)
    return "\n".join(en), ("\n".join(hi) or None), info


# --------------------------------------------------------------------------
# attachment text
# --------------------------------------------------------------------------
def _pdf_text(data: bytes) -> str:
    try:
        import pdfplumber  # noqa: WPS433

        with pdfplumber.open(io.BytesIO(data)) as pdf:
            return "\n".join((p.extract_text() or "") for p in pdf.pages[:ALERT_MAX_PDF_PAGES])
    except Exception as exc1:  # noqa: BLE001
        try:
            import pypdf  # noqa: WPS433

            return "\n".join((p.extract_text() or "") for p in pypdf.PdfReader(io.BytesIO(data), strict=False).pages[:ALERT_MAX_PDF_PAGES])
        except Exception as exc2:  # noqa: BLE001 - truncated / encrypted / not really a PDF
            log.warning("unreadable PDF (%s / %s) - skipped", str(exc1)[:80], str(exc2)[:80])
            return ""


TEXT_CACHE_DIR = OUT_ALERTS_DIR / "_textcache"      # extracted PDF text, keyed by name+size+mtime -> re-runs take seconds


def attachment_text(path: Path, use_cache: bool = True) -> str:
    if not path.exists():
        return ""
    cache = None
    if use_cache:
        st = path.stat()
        key = "%s|%d|%d" % (path.name, st.st_size, int(st.st_mtime))
        cache = TEXT_CACHE_DIR / (sha1(key, 20) + ".txt")
        if cache.exists():
            return cache.read_text(encoding="utf-8")
    text = _attachment_text_uncached(path)
    if cache is not None:
        try:
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(text, encoding="utf-8")
        except OSError:
            pass
    return text


def _attachment_text_uncached(path: Path) -> str:
    try:
        return _extract(path)
    except Exception as exc:  # noqa: BLE001 - corrupt zip etc.
        log.warning("attachment %s unreadable: %s", path.name, str(exc)[:100])
        return ""


def _extract(path: Path) -> str:
    data = path.read_bytes()
    if path.suffix.lower() == ".zip":
        parts = []
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            for n in zf.namelist():
                if n.lower().endswith(".pdf"):
                    parts.append(_pdf_text(zf.read(n)))
                elif n.lower().endswith((".txt", ".md")):
                    parts.append(zf.read(n).decode("utf-8", "replace"))
        return "\n".join(parts)
    if path.suffix.lower() == ".pdf":
        return _pdf_text(data)
    if path.suffix.lower() in (".txt", ".md", ".html", ".htm"):
        return path.read_text(encoding="utf-8", errors="replace")
    return ""


# --------------------------------------------------------------------------
# sectioning
# --------------------------------------------------------------------------
def split_sections(text: str) -> dict[str, str]:
    """Return {narrative, what_went_wrong, corrective_actions, references, other} from heading-delimited text."""
    lines = [clean_text(ln) for ln in text.splitlines()]
    sections: dict[str, list[str]] = {}
    current = "other"
    for ln in lines:
        if not ln:
            continue
        m = _HEADING_RE.match(ln)
        if m:
            current = ALERT_SECTION_MAP[m.group(1).lower()]
            sections.setdefault(current, [])
            continue
        # inline "What happened: text" on one line
        m2 = re.match(r"^(?:#+\s*)?(" + "|".join(re.escape(k) for k in ALERT_SECTION_MAP) + r")\s*[:\-]\s+(.+)$", ln, re.I)
        if m2:
            current = ALERT_SECTION_MAP[m2.group(1).lower()]
            sections.setdefault(current, []).append(m2.group(2))
            continue
        sections.setdefault(current, []).append(ln)
    out = {}
    for k, v in sections.items():
        out[k] = clean_text(reflow_pdf_lines(v), keep_newlines=True) or None
    return out


def _lsr_from(text: str, tags: list[str]) -> tuple[list[str], list[str]]:
    raw: list[str] = list(tags or [])
    for m in _LSR_LINE_RE.finditer(text[:4000]):
        raw += re.split(r"[,;/\n]|\band\b", m.group(1))
    found: list[str] = []
    unmapped: list[str] = []
    for r in raw:
        canon, un = canonical_lsr_list(r.strip(" .-"))
        found += [c for c in canon if c not in found]
        unmapped += un
    return found, unmapped


# --------------------------------------------------------------------------
# driver
# --------------------------------------------------------------------------
def _iter_source(source: str, cfg: dict):
    d = RAW_ALERTS_DIR / cfg["dir"]
    extra_present = any((RAW_ALERTS_DIR.parent / e).exists() for e in cfg.get("extra_dirs", []))
    if not d.exists() and not extra_present:
        return
    index = d / "index.jsonl"
    seen_files: set[str] = set()
    if index.exists():
        with open(index, "r", encoding="utf-8") as fh:
            for ln in fh:
                if ln.strip():
                    row = json.loads(ln)
                    for a in row.get("attachments", []):
                        seen_files.add(a["file"])
                    yield row
    # PDFs dropped manually (no index entry): <source>/files/ plus any extra_dirs under DATA/RAW (searched recursively)
    loose: list[tuple[Path, Path]] = []
    if (d / "files").exists():
        loose += [(d, p) for p in sorted((d / "files").glob("*"))]
    for extra in cfg.get("extra_dirs", []):
        ed = RAW_ALERTS_DIR.parent / extra
        if ed.exists() and ed.resolve() != d.resolve():
            loose += [(ed.parent, p) for p in sorted(ed.rglob("*")) if p.is_file()]
    for root, p in loose:
        rel = p.relative_to(root).as_posix()
        if rel not in seen_files and p.suffix.lower() in (".pdf", ".zip", ".txt") and not p.name.startswith("~$"):
            yield {"source": source, "url": None, "title": p.stem, "date": None, "tags": [], "html_text": "",
                   "attachments": [{"url": None, "file": rel}], "_root": str(root)}


def run(out_dir: Path = OUT_ALERTS_DIR) -> dict:
    rows: list[dict] = []
    per_source: dict[str, int] = {}
    for source, cfg in ALERT_SOURCES.items():
        d = RAW_ALERTS_DIR / cfg["dir"]
        n = 0
        for i, item in enumerate(_iter_source(source, cfg), start=1):
            root = Path(item["_root"]) if item.get("_root") else d
            html_text = (item.get("html_text") or "").strip()
            if cfg.get("prefer") == "html" and len(html_text) > 300:
                att_items, att_text, text_hi, att_info = [], "", None, {"attachments": len(item.get("attachments", [])), "languages": [], "skipped": "html preferred"}
            else:
                att_items = [(a["file"], attachment_text(root / a["file"])) for a in item.get("attachments", [])]
                att_text, text_hi, att_info = choose_attachment_texts(att_items)
            body = att_text.strip() if len(att_text.strip()) > 200 else html_text
            body = strip_boilerplate(body)
            body = re.sub(r"\n{3,}", "\n\n", body)
            if len(body) < MIN_TEXT_CHARS:
                continue
            secs = split_sections(body)
            narrative = secs.get("narrative") or _first_paragraph(secs.get("other") or body)
            lsr, unmapped = _lsr_from(body, item.get("tags") or [])
            text = narrative
            if narrative and word_count(narrative) < 12 and secs.get("what_went_wrong"):
                text = narrative.rstrip(".") + ". " + secs["what_went_wrong"]
            title = clean_text(str(item.get("title") or "")) or None
            oisd = oisd_header(body) if (source == "OISD" or "OISD/SA" in body[:600].upper().replace(" ", "")) else {}
            if oisd.get("title"):
                title = oisd["title"]
            off = source in MARINE_SOURCES and bool(_OFF_DOMAIN.search(f"{title} {body[:3000]}"))
            is_fatal = actual_fatality(body[:4000])
            outcome = oisd.get("actual_outcome") or outcome_code(title or "") or outcome_code((narrative or "") + " " + body[:1500])
            if is_fatal:
                outcome = "fatality"
            reference, ref_year = iadc_reference(body[:400], title=title, date=item.get("date"))
            reference = item.get("reference") or oisd.get("reference") or reference
            date = item.get("date") or oisd.get("date") or (str(ref_year) if ref_year else None)
            ref_year = oisd.get("year") or ref_year
            if ref_year is None and date:
                ref_year = int(date[:4]) if re.match(r"\d{4}", date) else None
            rows.append({
                "id": f"alert_{source.lower()}_{i:04d}",
                "source": f"alert_{source.lower()}",
                "alert_source": source,
                "record_type": ("fatal" if is_fatal else
                                "near_miss" if outcome == "near_miss" or _NM_RE.search((narrative or "") + " " + body[:1500]) else
                                "injury" if outcome in ("lost_time_injury", "restricted_work", "medical_treatment", "first_aid") or _INJ_RE.search(narrative or body[:2000]) else "incident"),
                "domain": cfg["domain"], "off_domain_marine": off,
                "title": title, "url": item.get("url"), "date": date, "reference": reference, "year": ref_year,
                "actual_outcome": outcome, "potential_consequence": potential_consequence((narrative or "") + " " + (secs.get("what_went_wrong") or "") + " " + body[:2500]),
                "text_hi": text_hi, "attachment_languages": att_info.get("languages", []),
                "location": oisd.get("location"), "activity": oisd.get("activity"), "loss_outcome": oisd.get("loss_outcome"), "segment": oisd.get("segment"),
                "tags": item.get("tags") or [], "life_saving_rules": lsr, "lsr_unmapped": unmapped,
                "text_source": "attachment" if len(att_text.strip()) > 200 else "html",
                "narrative": narrative, "what_went_wrong": secs.get("what_went_wrong"),
                "corrective_actions": secs.get("corrective_actions"), "references": secs.get("references"),
                "sections_found": [k for k in secs if secs[k]],
                "narrative_words": word_count(narrative or ""), "text": text,
                "actual_fatality": is_fatal,
                "actual_injury": (False if _NM_RE.search(narrative or "") else (bool(_INJ_RE.search(narrative or "")) or None)),
                "onshore_offshore": cfg["default_onshore_offshore"],
            })
            n += 1
        per_source[source] = n
        if n:
            log.info("%s: %d alerts parsed", source, n)
    if not rows:
        log.warning("no alerts found under %s - run `python -m CLEANING.fetch.fetch_alerts` on a machine with internet", RAW_ALERTS_DIR)
    dup = mark_duplicates(rows, text_field="text", id_field="id") if rows else {"exact_duplicates": 0, "near_duplicates": 0}
    stats = {
        "rows": len(rows), "per_source": per_source, "duplicates": dup,
        "by_record_type": _count(rows, "record_type"), "with_lsr": sum(1 for r in rows if r["life_saving_rules"]),
        "lsr_distribution": _lsr_dist(rows), "off_domain_marine": sum(1 for r in rows if r["off_domain_marine"]),
        "sections_narrative": sum(1 for r in rows if "narrative" in r["sections_found"]),
        "sections_what_went_wrong": sum(1 for r in rows if r["what_went_wrong"]),
        "text_from_attachment": sum(1 for r in rows if r["text_source"] == "attachment"),
        "by_actual_outcome": _count(rows, "actual_outcome"),
        "with_potential_consequence": sum(1 for r in rows if r["potential_consequence"]),
        "with_hindi_text": sum(1 for r in rows if r["text_hi"]),
        "attachments_skipped_other_language": sum(1 for r in rows for l in r["attachment_languages"] if l["lang"] not in ("en", "hi")),
    }
    write_jsonl(rows, out_dir / "alerts.jsonl")
    write_csv(rows, out_dir / "alerts.csv")
    write_json(stats, out_dir / "stats.json")
    return {"rows": rows, "stats": stats}


def _first_paragraph(text: str) -> str | None:
    if not text:
        return None
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if len(p.split()) >= 8]
    return clean_text(paras[0]) if paras else clean_text(text)[:1500] or None


def _lsr_dist(rows: list[dict]) -> dict:
    c: dict = {}
    for r in rows:
        for l in r["life_saving_rules"]:
            c[l] = c.get(l, 0) + 1
    return dict(sorted(c.items(), key=lambda kv: -kv[1]))


def _count(rows: list[dict], field: str) -> dict:
    out: dict = {}
    for r in rows:
        k = str(r.get(field))
        out[k] = out.get(k, 0) + 1
    return dict(sorted(out.items(), key=lambda kv: (-kv[1], kv[0])))


def warm_cache(budget_s: float = 150.0) -> dict:
    """Extract text from attachments that are not cached yet, stopping after `budget_s` seconds (resumable)."""
    import time  # noqa: WPS433

    t0, done, skipped, todo = time.time(), 0, 0, 0
    for source, cfg in ALERT_SOURCES.items():
        for item in _iter_source(source, cfg):
            root = Path(item["_root"]) if item.get("_root") else RAW_ALERTS_DIR / cfg["dir"]
            if cfg.get("prefer") == "html" and len((item.get("html_text") or "").strip()) > 300:
                continue
            for a in item.get("attachments", []):
                p = root / a["file"]
                if not p.exists():
                    continue
                st = p.stat()
                cache = TEXT_CACHE_DIR / (sha1("%s|%d|%d" % (p.name, st.st_size, int(st.st_mtime)), 20) + ".txt")
                if cache.exists():
                    skipped += 1
                    continue
                if time.time() - t0 > budget_s:
                    todo += 1
                    continue
                attachment_text(p)
                done += 1
    out = {"extracted_now": done, "already_cached": skipped, "remaining": todo, "seconds": round(time.time() - t0, 1)}
    log.info("warm_cache: %s", out)
    return out


if __name__ == "__main__":  # pragma: no cover
    import argparse  # noqa: WPS433

    ap = argparse.ArgumentParser(description="Parse safety alerts (or just pre-extract PDF text into the cache)")
    ap.add_argument("--warm-cache", action="store_true", help="only extract attachment text into _textcache, then stop")
    ap.add_argument("--budget", type=float, default=150.0, help="seconds to spend when warming the cache")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    if a.warm_cache:
        print(json.dumps(warm_cache(a.budget)))
    else:
        run()
