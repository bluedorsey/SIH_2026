"""Data-quality report (Markdown) + manifest (JSON) for one pipeline run."""
from __future__ import annotations

import json
import platform
import sys
from datetime import datetime
from pathlib import Path

from .common.io import write_json
from .config import OUT_MANIFEST_JSON, OUT_REPORT_MD, PROCESSED_DIR


def _fmt_counts(d: dict, limit: int = 15) -> str:
    items = list(d.items())[:limit]
    return ", ".join(f"{k}: {v}" for k, v in items) + (" …" if len(d) > limit else "")


def _len_stats(rows: list[dict], field: str = "text") -> str:
    ws = sorted(len((r.get(field) or "").split()) for r in rows)
    if not ws:
        return "n/a"
    return f"min {ws[0]} / median {ws[len(ws) // 2]} / p90 {ws[int(len(ws) * 0.9)]} / max {ws[-1]} words"


def write_report(results: dict, elapsed_s: float) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines: list[str] = [f"# Data quality report", "", f"Generated {now} · {elapsed_s:.0f}s · Python {platform.python_version()}", ""]

    iogp = results.get("iogp")
    if iogp and not iogp.get("loaded_from_disk"):
        recs, log = iogp["records"], iogp["log"]
        lines += ["## IOGP fatal / HiPo / permanent-impairment PDFs", ""]
        lines += ["| file | type | year | pages | records | with warnings |", "|---|---|---|---|---|---|"]
        for f in log["files"]:
            lines.append(f"| {f['file']} | {f['record_type']} | {f['year']} | {f['pages']} | {f['records']} | {f['records_with_warnings']} |")
        lines += ["", f"Skipped: " + "; ".join(f"`{s['file']}` ({s['reason']})" for s in log["skipped"]), ""]
        by_type: dict = {}
        for r in recs:
            by_type[r["record_type"]] = by_type.get(r["record_type"], 0) + 1
        lsr: dict = {}
        for r in recs:
            for l in r["life_saving_rules"]:
                lsr[l] = lsr.get(l, 0) + 1
        lsr = dict(sorted(lsr.items(), key=lambda kv: -kv[1]))
        warn: dict = {}
        for r in recs:
            for w in r["parse_warnings"]:
                k = w.split(":")[0]
                warn[k] = warn.get(k, 0) + 1
        lines += [
            f"- **{len(recs)} records** - {_fmt_counts(by_type)}",
            f"- narrative length: {_len_stats(recs, 'narrative')}",
            f"- records with a Life-Saving Rule: {sum(1 for r in recs if r['life_saving_rules'])} "
            f"({sum(1 for r in recs if not r['life_saving_rules'])} say 'no applicable rule' / unspecified)",
            f"- LSR distribution: {_fmt_counts(lsr)}",
            f"- records with parsed causal factors: {sum(1 for r in recs if r['causal_factors'])}",
            f"- warnings: {_fmt_counts(warn) or 'none'}",
            "",
        ]

    osha = results.get("osha")
    if osha and not osha.get("loaded_from_disk"):
        st = osha["stats"]
        lines += ["## OSHA Severe Injury Reports", ""]
        lines += [
            f"- raw rows: {st['raw_rows']} (dropped {st['dropped_empty_or_short_narrative']} with empty/short narrative)",
            f"- **oil & gas subset: {st['oilgas_rows']} rows**, {st['oilgas_unique_for_training']} unique after de-duplication "
            f"({st['oilgas_duplicates']['exact_duplicates']} exact + {st['oilgas_duplicates']['near_duplicates']} near duplicates)",
            f"- by sector: {_fmt_counts(st['oilgas_by_sector'])}",
            f"- by year: {_fmt_counts(dict(sorted(st['oilgas_by_year'].items())))}",
            f"- actual severity: {_fmt_counts(st['oilgas_severity'])}",
            f"- narrative length: {_len_stats(osha['oilgas'])}",
            f"- unparsed dates: {st['date_unparsed']}, missing NAICS: {st['naics_missing']}",
            "",
        ]

    reg = results.get("register")
    if reg and not reg.get("loaded_from_disk"):
        lines += ["## Register-style logs", ""]
        for st in reg["stats"]:
            lines += [
                f"### {st['file']}",
                f"- rows: {st['rows']} (raw {st['raw_rows']}, dropped {st['dropped_empty_or_short']})",
                f"- column mapping: " + ", ".join(f"`{k}` → {v}" for k, v in st["column_mapping"].items()),
                f"- unmapped columns: {st['unmapped_columns'] or 'none'}",
                f"- category: {_fmt_counts(st['category_counts'])}; sub-category: {_fmt_counts(st['sub_category_counts'])}",
                f"- areas: {_fmt_counts(st['area_counts'])}",
                f"- dates unparsed: {st['date_unparsed']} (year assumed for {st['date_year_assumed']}) - pass `--register-year YYYY` if the register omits the year",
                f"- description words min/median/max: {st['words_min_median_max']}",
                f"- duplicates: {st['duplicates']['exact_duplicates']} exact, {st['duplicates']['near_duplicates']} near",
                "",
            ]

    terms = results.get("terms")
    if terms:
        st = terms["stats"]
        lines += ["## terms.json glossary", ""]
        lines += [
            f"- {st['raw_entries']} raw entries → **{st['unique_terms']} unique terms**, {st['total_variants']} variants",
            f"- duplicate terms merged: {st['duplicate_terms_merged']} ({st['entries_with_conflicts']} with conflicting fields - see `merge_conflicts`)",
            f"- by category: {_fmt_counts(st['by_category'])}",
            f"- by safety_signal (GLiNER role): {_fmt_counts(st['by_safety_signal'])}",
            f"- by Life-Saving Rule: {_fmt_counts(st['by_lsr'])}",
            f"- variants shared by two terms (first wins in lookup): {len(st['variant_collisions'])}",
            f"- schema problems: {len(st['schema_problems'])}",
            "",
        ]

    for key, title in (("gold", "Gold-180 (Hinglish gold set)"), ("osha_abstracts", "OSHA accident abstracts (16k, GitHub mirror)"),
                       ("ihm", "Kaggle IHM (eval only)"), ("msha", "MSHA accidents"), ("alerts", "Safety alerts (IADC / IMCA / Step Change / OISD)")):
        res = results.get(key)
        if not res or res.get("loaded_from_disk"):
            continue
        st = res["stats"]
        lines += [f"## {title}", ""]
        for k, v in st.items():
            if isinstance(v, dict) and len(v) > 25:
                v = dict(list(v.items())[:25])
            if isinstance(v, list) and len(v) > 10:
                v = v[:10]
            lines.append(f"- {k}: {json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v}")
        lines.append("")

    uni = results.get("unified")
    if uni:
        st = uni["stats"]
        lines += ["## Unified corpus", ""]
        lines += [
            f"- **{st['total']} rows, {st['unique']} unique** ({st['duplicates']['exact_duplicates']} exact + {st['duplicates']['near_duplicates']} near duplicates flagged, not removed)",
            f"- by source: {_fmt_counts(st['by_source'])}",
            f"- by record type: {_fmt_counts(st['by_record_type'])}",
            f"- by teacher prompt: {_fmt_counts(st['by_teacher_prompt'])} (rewind = prompts.md §2, label = §3)",
            f"- `teacher_input.jsonl` has {st['unique']} de-duplicated rows ready for the teacher LLM",
            "",
        ]

    lines += ["## Output files", ""]
    for p in sorted(PROCESSED_DIR.rglob("*")):
        if p.is_file() and p.name not in (OUT_REPORT_MD.name,):
            lines.append(f"- `{p.relative_to(PROCESSED_DIR).as_posix()}` ({p.stat().st_size / 1024:.0f} KB)")
    OUT_REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(results: dict, args: dict, elapsed_s: float) -> None:
    manifest = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "args": args,
        "elapsed_seconds": round(elapsed_s, 1),
        "sources": {},
        "outputs": [],
    }
    if results.get("iogp") and not results["iogp"].get("loaded_from_disk"):
        manifest["sources"]["iogp"] = results["iogp"]["log"]
    if results.get("osha") and not results["osha"].get("loaded_from_disk"):
        manifest["sources"]["osha"] = results["osha"]["stats"]
    if results.get("register") and not results["register"].get("loaded_from_disk"):
        manifest["sources"]["register"] = results["register"]["stats"]
    if results.get("terms"):
        st = dict(results["terms"]["stats"])
        st.pop("schema_problems", None)
        manifest["sources"]["terms"] = st
    if results.get("unified"):
        manifest["sources"]["unified"] = results["unified"]["stats"]
    for key in ("gold", "osha_abstracts", "ihm", "msha", "alerts"):
        if results.get(key) and not results[key].get("loaded_from_disk"):
            st = dict(results[key]["stats"])
            for big in ("by_year", "schema_problems"):
                st.pop(big, None)
            manifest["sources"][key] = st
    for p in sorted(PROCESSED_DIR.rglob("*")):
        if p.is_file() and p.name != OUT_MANIFEST_JSON.name:
            manifest["outputs"].append({"path": p.relative_to(PROCESSED_DIR).as_posix(), "bytes": p.stat().st_size})
    write_json(manifest, OUT_MANIFEST_JSON)
