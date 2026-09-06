"""
IOGP fatal / high-potential / permanent-impairment PDF -> records.jsonl

Input : DATA/RAW/IOGP_HiPo fatal/*.pdf
Output: DATA/Processed/iogp/records.jsonl   (one incident per line)
        DATA/Processed/iogp/records.csv     (same, flat, for Excel)
        DATA/Processed/iogp/parse_log.json  (per-file counts + skipped files)

What it handles
- only the narrative reports (suffix sf / sh / fpi); statistics reports (s, f, fe, ae) are skipped
- byte-identical duplicate PDFs ("2024sf (1).pdf") are skipped by hash
- page headers, page numbers, region headings, front matter
- records that cross page boundaries
- 2022 layout (single "RULE:") vs 2023+ (PRIMARY / SECONARY [sic] LIFE-SAVING RULE)
- "NARRATIVE:" landing mid-line after an empty "Time in service:" field
- victim block ("FATALITY" / "WORKFORCE PERMANENT IMPAIRMENT") parsed into fields
- causal factors parsed into {group, category, factor}
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path

from .common.io import file_sha256, write_csv, write_json, write_jsonl
from .common.lsr import canonical_lsr_list
from .common.text import clean_text, reflow_pdf_lines, sha1, word_count
from .config import (
    IOGP_META_LABELS,
    IOGP_REGIONS,
    IOGP_SECTION_LABELS,
    IOGP_SUFFIX_TO_TYPE,
    IOGP_VICTIM_BLOCK_HEADERS,
    IOGP_VICTIM_FIELDS,
    OUT_IOGP_DIR,
    RAW_IOGP_DIR,
)

log = logging.getLogger("clean.iogp")

_FILENAME_RE = re.compile(r"^(?P<year>20\d{2})(?P<suffix>[a-z]+)(?:\s*\(\d+\))?\.pdf$", re.I)
_PAGE_HEADER_RES = [
    re.compile(r"^\d{4} safety data\s*[-–]\s*.*reports?$", re.I),
    re.compile(r"^Safety performance indicators\s*[-–].*$", re.I),
    re.compile(r"^IOGP permanent impairment incidents\s+\d{4}$", re.I),
    re.compile(r"^Contents$", re.I),
    re.compile(r"^\d{1,3}$"),                     # page number
]
_SECTION_LABELS_RE = re.compile(
    r"(?:(?<=\s)|^)(" + "|".join(re.escape(k) for k in IOGP_SECTION_LABELS) + r"):\s*", re.M
)
_META_LINE_RE = re.compile(r"^([A-Z][A-Z /\-&()]+?)\s*[:;]\s*(.*)$")
_VICTIM_FIELD_RE = re.compile(
    r"(" + "|".join(re.escape(k) for k in IOGP_VICTIM_FIELDS) + r"):\s*"
)
_CAUSAL_LINE_RE = re.compile(r"^(PEOPLE \(ACTS\)|PROCESS \(CONDITIONS\))\s*:\s*(.*)$")
_DATE_FORMATS = ("%d %b %Y", "%b %d %Y", "%d %B %Y", "%B %d %Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d %b %y")


# PDF text extraction
def extract_pages(pdf_path: Path) -> list[str]:
    """Return page texts.

    pdfplumber is the primary extractor: on these InDesign PDFs pypdf drops the
    region headings on some files and glues them onto the previous line on
    others ("...safe isolation.NORTH AMERICA ONSHORE"), which breaks region
    tracking.  pypdf is kept as a fallback so the pipeline still runs if
    pdfplumber is missing.
    """
    try:
        import pdfplumber  # noqa: WPS433

        with pdfplumber.open(str(pdf_path)) as pdf:
            return [(p.extract_text() or "") for p in pdf.pages]
    except ImportError:
        log.warning("pdfplumber not installed - falling back to pypdf (region headings may be lost)")
    except Exception as exc:  # pragma: no cover
        log.warning("pdfplumber failed on %s (%s); falling back to pypdf", pdf_path.name, exc)
    import pypdf  # noqa: WPS433

    reader = pypdf.PdfReader(str(pdf_path))
    return [(p.extract_text() or "") for p in reader.pages]


def _is_page_header(line: str) -> bool:
    return any(rx.match(line) for rx in _PAGE_HEADER_RES)


def pdf_to_lines(pages: list[str]) -> list[tuple[str, int]]:
    """Flatten pages to (line, page_no) tuples, dropping headers / footers / blank lines."""
    out: list[tuple[str, int]] = []
    for pno, page in enumerate(pages, start=1):
        for raw in page.splitlines():
            ln = clean_text(raw)
            if not ln or _is_page_header(ln):
                continue
            out.append((ln, pno))
    return out


# Record splitting
def split_records(lines: list[tuple[str, int]]) -> list[dict]:
    """Group lines into raw records, tracking the current region heading."""
    records: list[dict] = []
    region = None
    cur: dict | None = None
    started = False
    for ln, pno in lines:
        if ln.upper() in IOGP_REGIONS:
            region = ln.upper()
            continue
        if ln.startswith("DATE:"):
            started = True
            cur = {"region": region, "page_start": pno, "lines": [ln]}
            records.append(cur)
            continue
        if not started or cur is None:
            continue  # front matter
        cur["lines"].append(ln)
        cur["page_end"] = pno
    return records


# Field parsing
def parse_date(raw: str | None) -> str | None:
    if not raw:
        return None
    s = re.sub(r"(\d)(st|nd|rd|th)\b", r"\1", raw.strip().replace(",", ""))
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def parse_victim_block(text: str) -> dict:
    """'Function: Drilling, Employer: Contractor, Occupation: ...' -> dict."""
    out: dict = {}
    parts = _VICTIM_FIELD_RE.split(text)
    # parts = [prefix, label, value, label, value, ...]
    for i in range(1, len(parts) - 1, 2):
        label, value = parts[i], parts[i + 1]
        value = value.strip().strip(",;").strip()
        field = IOGP_VICTIM_FIELDS[label]
        if field in ("lwdc_days", "rwdc_days"):
            m = re.match(r"\d+", value)
            out[field] = int(m.group()) if m else None
        else:
            out[field] = value or None
    return out


def parse_causal_factors(text: str) -> list[dict]:
    """Each line 'PEOPLE (ACTS): Category: Factor' -> {group, category, factor}."""
    if not text or re.search(r"no causal factors? allocated", text, re.I):
        return []
    items: list[dict] = []
    for ln in text.splitlines():
        m = _CAUSAL_LINE_RE.match(ln.strip())
        if not m:
            # continuation of the previous factor (PDF wrap)
            if items and ln.strip():
                items[-1]["factor"] = ((items[-1]["factor"] or "") + " " + ln.strip()).strip()
            continue
        group, rest = m.group(1), m.group(2)
        cat, _, factor = rest.partition(":")
        items.append({
            "group": "people_acts" if group.startswith("PEOPLE") else "process_conditions",
            "category": cat.strip(),
            "factor": factor.strip() or None,
        })
    # de-duplicate identical factors (IOGP sometimes lists the same one twice)
    seen: set[tuple] = set()
    uniq: list[dict] = []
    for it in items:
        key = (it["group"], it["category"], it["factor"])
        if key not in seen:
            seen.add(key)
            uniq.append(it)
    return uniq


def parse_record(rec: dict, *, year: int, record_type: str, source_file: str, idx: int) -> dict:
    """Turn a raw {'lines': [...]} record into a clean, typed dict."""
    body = "\n".join(rec["lines"])
    # force every section label onto its own line (handles "Time in service: NARRATIVE:")
    body = _SECTION_LABELS_RE.sub(lambda m: "\n" + m.group(1) + ":\n", body)

    meta: dict = {}
    sections: dict[str, list[str]] = {}
    victim_lines: list[str] = []
    current_section: str | None = None
    in_victim_block = False

    for ln in body.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        upper = ln.rstrip(":").strip()
        # section header?
        if ln.endswith(":") and upper in IOGP_SECTION_LABELS:
            current_section = IOGP_SECTION_LABELS[upper]
            sections.setdefault(current_section, [])
            in_victim_block = False
            continue
        # victim block header?
        if upper in IOGP_VICTIM_BLOCK_HEADERS and current_section is None:
            in_victim_block = True
            continue
        # single-line metadata?
        if current_section is None:
            m = _META_LINE_RE.match(ln)
            if m and m.group(1) in IOGP_META_LABELS:
                meta[IOGP_META_LABELS[m.group(1)]] = m.group(2).strip()
                in_victim_block = False
                continue
            if in_victim_block or _VICTIM_FIELD_RE.search(ln):
                victim_lines.append(ln)
                in_victim_block = True
                continue
            # unknown line before any section - keep it so nothing is silently lost
            sections.setdefault("_unparsed_header", []).append(ln)
            continue
        sections[current_section].append(ln)

    def section_text(name: str) -> str | None:
        if name not in sections or not sections[name]:
            return None
        return clean_text(reflow_pdf_lines(sections[name]), keep_newlines=True) or None

    narrative = section_text("narrative")
    what_went_wrong = section_text("what_went_wrong")
    corrective = section_text("corrective_actions")
    causal_raw = "\n".join(sections.get("causal_factors_raw", []))
    unparsed = section_text("_unparsed_header")

    lsr_primary, unmapped_p = canonical_lsr_list(meta.get("lsr_primary_raw"))
    lsr_secondary, unmapped_s = canonical_lsr_list(meta.get("lsr_secondary_raw"))
    lsr_all = list(dict.fromkeys(lsr_primary + lsr_secondary))

    victim = parse_victim_block(" ".join(victim_lines)) if victim_lines else {}

    def cat(v: str | None) -> str | None:
        """Categorical value: 2023sf shouts 'DRILLING' where every other year says 'Drilling'."""
        if not v:
            return None
        v = v.strip()
        return v.capitalize() if v.isupper() and len(v) > 3 else v

    def to_int(v: str | None) -> int | None:
        if v is None:
            return None
        m = re.match(r"\d+", v)
        return int(m.group()) if m else None

    content_key = sha1((narrative or "") + "|" + (meta.get("date_raw") or "") + "|" + (meta.get("country") or ""))
    out = {
        "id": f"iogp_{year}_{record_type}_{idx:03d}_{content_key[:6]}",
        "source": "iogp",
        "record_type": record_type,            # fatal | hipo | permanent_impairment
        "report_year": year,
        "source_file": source_file,
        "page_start": rec.get("page_start"),
        "page_end": rec.get("page_end", rec.get("page_start")),
        "region": rec.get("region"),
        "onshore_offshore": (rec["region"].split()[-1].lower() if rec.get("region") else None),
        "date_raw": meta.get("date_raw"),
        "date": parse_date(meta.get("date_raw")),
        "country": cat(meta.get("country")),
        "function": cat(meta.get("function")),
        "cause": cat(meta.get("cause")),
        "activity": cat(meta.get("activity")),
        "number_of_deaths": to_int(meta.get("number_of_deaths")),
        "number_of_pi_injuries": to_int(meta.get("number_of_pi_injuries")),
        "lsr_primary_raw": meta.get("lsr_primary_raw"),
        "lsr_secondary_raw": meta.get("lsr_secondary_raw"),
        "lsr_primary": lsr_primary[0] if lsr_primary else None,
        "lsr_secondary": lsr_secondary[0] if lsr_secondary else None,
        "life_saving_rules": lsr_all,
        "lsr_unmapped": unmapped_p + unmapped_s,
        **{k: victim.get(k) for k in IOGP_VICTIM_FIELDS.values()},
        "narrative": narrative,
        "what_went_wrong": what_went_wrong,
        "corrective_actions": corrective,
        "causal_factors": parse_causal_factors(causal_raw),
        "causal_factors_raw": clean_text(causal_raw, keep_newlines=True) or None,
        "unparsed_header_lines": unparsed,
        "narrative_words": word_count(narrative or ""),
    }
    # `text` is the field every downstream step reads.  IOGP sometimes uses the
    # narrative as a one-line title ("Battery fire.") and puts the story in
    # WHAT WENT WRONG - in that case join the two so the teacher sees the event.
    if narrative and out["narrative_words"] < 12 and what_went_wrong and word_count(what_went_wrong) > out["narrative_words"]:
        out["text"] = narrative.rstrip(".") + ". " + what_went_wrong
        out["text_composition"] = "narrative+what_went_wrong"
    else:
        out["text"] = narrative
        out["text_composition"] = "narrative"
    out["parse_warnings"] = _warnings(out)
    return out


def _warnings(r: dict) -> list[str]:
    w: list[str] = []
    if not r["narrative"]:
        w.append("missing_narrative")
    elif r["narrative_words"] < 8:
        w.append("very_short_narrative")
    if not r["life_saving_rules"]:
        w.append("no_lsr")
    if r["lsr_unmapped"]:
        w.append("lsr_unmapped:" + "|".join(r["lsr_unmapped"]))
    if r["date"] is None:
        w.append("date_unparsed")
    if r["record_type"] == "fatal" and not r["number_of_deaths"]:
        w.append("fatal_without_death_count")
    if r["unparsed_header_lines"]:
        w.append("unparsed_header_lines")
    return w


# Driver
def classify_pdf(path: Path) -> tuple[int | None, str | None]:
    m = _FILENAME_RE.match(path.name)
    if not m:
        return None, None
    return int(m.group("year")), IOGP_SUFFIX_TO_TYPE.get(m.group("suffix").lower())


def run(raw_dir: Path = RAW_IOGP_DIR, out_dir: Path = OUT_IOGP_DIR) -> dict:
    records: list[dict] = []
    parse_log: dict = {"files": [], "skipped": []}
    seen_hashes: dict[str, str] = {}

    # "2024sf.pdf" must be seen before its Windows copy "2024sf (1).pdf" so the clean name is the one kept
    def _order(p: Path) -> tuple:
        n = p.name.lower()
        return (re.sub(r"\s*\(\d+\)(?=\.pdf$)", "", n), bool(re.search(r"\(\d+\)\.pdf$", n)), n)

    for pdf in sorted(raw_dir.glob("*.pdf"), key=_order):
        year, rtype = classify_pdf(pdf)
        if rtype is None:
            parse_log["skipped"].append({"file": pdf.name, "reason": "not a narrative report (statistics / summary)"})
            log.info("skip %-22s statistics/summary report", pdf.name)
            continue
        digest = file_sha256(pdf)
        if digest in seen_hashes:
            parse_log["skipped"].append({"file": pdf.name, "reason": f"byte-identical duplicate of {seen_hashes[digest]}"})
            log.info("skip %-22s duplicate of %s", pdf.name, seen_hashes[digest])
            continue
        seen_hashes[digest] = pdf.name

        pages = extract_pages(pdf)
        lines = pdf_to_lines(pages)
        raw_recs = split_records(lines)
        parsed = [
            parse_record(rr, year=year, record_type=rtype, source_file=pdf.name, idx=i + 1)
            for i, rr in enumerate(raw_recs)
        ]
        n_warn = sum(1 for r in parsed if r["parse_warnings"])
        parse_log["files"].append({
            "file": pdf.name, "sha256": digest, "year": year, "record_type": rtype,
            "pages": len(pages), "records": len(parsed), "records_with_warnings": n_warn,
        })
        log.info("ok   %-22s %-22s %3d records (%d with warnings)", pdf.name, rtype, len(parsed), n_warn)
        records.extend(parsed)

    parse_log["total_records"] = len(records)
    write_jsonl(records, out_dir / "records.jsonl")
    write_csv(records, out_dir / "records.csv")
    write_json(parse_log, out_dir / "parse_log.json")
    return {"records": records, "log": parse_log}


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    run()
