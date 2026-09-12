"""
Smoke tests for the cleaning pipeline - no raw data needed.

    python -m CLEANING.test_cleaning      (or: pytest CLEANING/test_cleaning.py)
"""
from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    __package__ = "CLEANING"  # noqa: A001

from .clean_alerts import split_sections  # noqa: E402
from .clean_gold import map_barrier, trap_family, verdict_candidates  # noqa: E402
from .clean_iogp import parse_causal_factors, parse_date, parse_record, parse_victim_block, split_records  # noqa: E402
from .clean_msha import _sentence_case  # noqa: E402
from .clean_osha_abstracts import oilgas_score  # noqa: E402
from .evaluate_readiness import _lang  # noqa: E402
from .clean_register import map_columns  # noqa: E402
from .clean_terms import _flatten, clean_entries  # noqa: E402
from .common.dedup import mark_duplicates  # noqa: E402
from .common.lsr import canonical_lsr, canonical_lsr_list  # noqa: E402
from .common.text import clean_text, dedup_key, reflow_pdf_lines  # noqa: E402


def test_text_normalisation():
    assert clean_text("  Hello  “world” – ok​ ") == 'Hello "world" - ok'
    assert clean_text("LOTO नहीं किया") == "LOTO नहीं किया"          # Devanagari untouched
    assert clean_text("isolaton not done") == "isolaton not done"    # typos untouched
    assert dedup_key("Hello, World!!") == dedup_key("hello world")
    assert reflow_pdf_lines(["tools/equipment/", "materials", "• item", "cont."]) == "tools/equipment/materials\n• item cont."


def test_lsr_mapping():
    assert canonical_lsr("Bypassing safety controls") == "Bypassing Safety Controls"
    assert canonical_lsr("Work authorization") == "Work Authorisation"
    assert canonical_lsr("Lifting Operations") == "Safe Mechanical Lifting"
    assert canonical_lsr("Other issue - no applicable rule") is None
    assert canonical_lsr("null") is None
    assert canonical_lsr_list("Line of fire / Safe mechanical lifting") == (["Line of Fire", "Safe Mechanical Lifting"], [])
    assert canonical_lsr_list("Foo bar") == ([], ["Foo bar"])


IOGP_SAMPLE = [
    ("AFRICA ONSHORE", 5),
    ("DATE: 07 Mar 2024", 5), ("COUNTRY: Egypt", 5), ("NUMBER OF DEATHS: 1", 5), ("FUNCTION; DRILLING", 5),
    ("CAUSE: Falls from height", 5), ("ACTIVITY: Drilling, workover, well operations", 5),
    ("PRIMARY LIFE-SAVING RULE: Confined space", 5), ("SECONARY LIFE-SAVING RULE: Work authorization", 5),
    ("FATALITY", 5),
    ("Function: Drilling, Employer: Contractor, Occupation: Process/equipment operator, Body part: Head (incl. mouth,", 5),
    ("etc.), Nature of injury: Unspecified, Time in service: NARRATIVE:", 5),
    ("The IP was using the ladder to get inside the batch mixer and fell", 5),
    ("from approximately 1 m height, hitting his head.", 6),
    ("WHAT WENT WRONG:", 6), ("• Access to tank was not part of the authorized activity.", 6),
    ("• No Stop Work Authority was applied.", 6),
    ("CORRECTIVE ACTIONS AND RECOMMENDATIONS:", 6), ("Always follow PTW.", 6),
    ("CAUSAL FACTORS:", 6),
    ("PEOPLE (ACTS): Following Procedures: Deviation intentional (by individual or group)", 6),
    ("PROCESS (CONDITIONS): Tools, Equipment, Materials and Products: Inadequate design/specification/management", 6),
    ("of change", 6),
    ("PEOPLE (ACTS): Following Procedures: Deviation intentional (by individual or group)", 6),
    ("DATE: 13 Jun 2024", 6), ("COUNTRY: Gabon", 6), ("FUNCTION: Drilling", 6), ("CAUSE: Struck by", 6),
    ("ACTIVITY: Transport", 6), ("RULE: Other issue - no applicable rule", 6),
    ("NARRATIVE:", 6), ("Battery fire.", 6), ("WHAT WENT WRONG:", 6),
    ("Emergency shutdown on wells failed to close and water tanks ran over.", 6),
    ("CORRECTIVE ACTIONS AND RECOMMENDATIONS:", 6), ("Fix it.", 6), ("CAUSAL FACTORS:", 6), ("No Causal Factors Allocated", 6),
]


def test_iogp_parse():
    raw = split_records(IOGP_SAMPLE)
    assert len(raw) == 2 and raw[0]["region"] == "AFRICA ONSHORE" and raw[0]["page_start"] == 5
    r = parse_record(raw[0], year=2024, record_type="fatal", source_file="2024sf.pdf", idx=1)
    assert r["date"] == "2024-03-07" and r["country"] == "Egypt" and r["function"] == "Drilling"
    assert r["number_of_deaths"] == 1
    assert r["life_saving_rules"] == ["Confined Space", "Work Authorisation"]
    assert r["victim_employer"] == "Contractor" and r["victim_body_part"] == "Head (incl. mouth, etc.)"
    assert r["victim_time_in_service"] is None
    assert r["narrative"].startswith("The IP was using the ladder") and r["narrative"].endswith("hitting his head.")
    assert r["what_went_wrong"].count("\n") == 1          # two bullets stay on two lines
    assert len(r["causal_factors"]) == 2                     # duplicate factor collapsed
    assert r["causal_factors"][1]["factor"] == "Inadequate design/specification/management of change"
    assert r["page_end"] == 6 and not r["parse_warnings"]

    r2 = parse_record(raw[1], year=2024, record_type="hipo", source_file="2024sh.pdf", idx=2)
    assert r2["life_saving_rules"] == [] and r2["lsr_unmapped"] == [] and "no_lsr" in r2["parse_warnings"]
    assert r2["text_composition"] == "narrative+what_went_wrong"
    assert r2["causal_factors"] == []


def test_iogp_helpers():
    assert parse_date("Aug 8 2024") == "2024-08-08" and parse_date("24 Oct 2024") == "2024-10-24"
    v = parse_victim_block("PI Category: Permanent loss of body parts LWDC Days: 35 RWDC Days: Function: Drilling Employer: Contractor")
    assert v["lwdc_days"] == 35 and v["rwdc_days"] is None and v["victim_function"] == "Drilling"
    assert parse_causal_factors("No Causal Factors Allocated") == []


def test_dedup():
    rows = [
        {"id": "a", "text": "Worker fell from scaffold at 6 m, no harness.", "rt": "hipo"},
        {"id": "b", "text": "Worker fell from scaffold at 6 m - no harness!", "rt": "fatal"},   # exact after normalisation
        {"id": "c", "text": "Slipped on oil spill near pump house, minor bruise.", "rt": "near_miss"},
        {"id": "d", "text": "During the lifting operation the crane load swung and struck the rigger who was standing in the drop zone without a tag line, causing a fractured arm and hospitalisation.", "rt": "hipo"},
        {"id": "e", "text": "During the lifting operation the crane load swung and struck the rigger who was standing in the drop zone without a tag line causing a fractured arm and hospitalisation", "rt": "permanent_impairment"},
    ]
    stats = mark_duplicates(rows, priority=lambda r: {"fatal": 3, "permanent_impairment": 2}.get(r["rt"], 0))
    by = {r["id"]: r for r in rows}
    assert by["a"]["is_duplicate"] and by["a"]["duplicate_of"] == "b" and not by["b"]["is_duplicate"]
    assert by["b"]["duplicate_ids"] == ["a"]
    assert not by["c"]["is_duplicate"]
    assert by["d"]["is_duplicate"] and by["d"]["duplicate_of"] == "e"
    assert stats["exact_duplicates"] >= 1


def test_register_mapping():
    m = map_columns(["S/No.", "Date Raised", "Near miss description (Observation)", "Category", "Near miss Observation",
                     "Area(Location)", "Raised By(Observer)", "Status", "Corrective action/Follow up", "Sub-location", "Weird"])
    assert m["Near miss description (Observation)"] == "description"
    assert m["Near miss Observation"] == "sub_category"
    assert m["Area(Location)"] == "area" and m["Sub-location"] == "sub_location"
    assert m["Raised By(Observer)"] == "observer" and "Weird" not in m


def test_terms():
    raw = _flatten([{"term": "PSV", "variants": ["psv", "safety valve"], "lsr": "null", "safety_signal": "none"},
                    [{"term": "psv", "variants": ["relief valve", "PSV"], "lsr": "Work Authorization", "safety_signal": "outcome"}]])
    assert len(raw) == 2
    entries, stats = clean_entries(raw)
    assert stats["unique_terms"] == 1 and stats["duplicate_terms_merged"] == 1
    e = entries[0]
    assert e["variants"] == ["safety valve", "relief valve"]
    assert e["lsr"] == "Work Authorisation" and e["safety_signal"] == "outcome_cue"


def test_alert_sections():
    txt = "IMCA SF 15/26\nWhat happened?\nA crew member sustained a hand injury during a lifting operation.\nThe chain block\ntravelled off the beam.\nWhat went wrong?\n- No end stops fitted.\nLessons learned\n- Inspect all beams.\nLife Saving Rules referenced: Safe mechanical lifting, Working at height"
    secs = split_sections(txt)
    assert secs["narrative"].startswith("A crew member sustained") and "travelled off the beam" in secs["narrative"]
    assert secs["what_went_wrong"].startswith("- No end stops")
    assert secs["corrective_actions"].startswith("- Inspect")
    inline = split_sections("WHAT HAPPENED: A dropped object fell 8 m.\nCORRECTIVE ACTIONS: Tether tools.")
    assert inline["narrative"] == "A dropped object fell 8 m." and inline["corrective_actions"] == "Tether tools."


def test_gold_mapping():
    assert map_barrier("isolation and LOTO verification") == "energy_isolation"
    assert map_barrier("gas test and entry permit") == "gas_test"
    assert map_barrier("fall protection") == "fall_arrest"
    assert map_barrier("goggles") == "ppe"
    assert map_barrier("none") is None
    assert trap_family("india_monsoon") == "india_context" and trap_family("duplicate_cluster_A") == "duplicate_cluster"
    assert verdict_candidates("YES", "historical", ["gravity"], "absent", "present", "worker fell") == ["NON_EVENT"]
    assert verdict_candidates("NO", "observed", [], None, "present", "small cut") == ["LOW_ENERGY", "NON_EVENT"]
    assert verdict_candidates("YES", "observed", ["gravity"], "present_effective", "present", "scaffold pole gir gaya, lanyard caught it")[0] == "CAPACITY"


def test_domain_and_language():
    score, terms = oilgas_score("A floorhand on the drilling rig was struck by the tongs near the catwalk.")
    assert score >= 4 and "drilling rig" in terms
    assert oilgas_score("Employee fell from a billboard catwalk.")[0] == 1   # weak term only -> not oil & gas
    assert _sentence_case("EMPLOYEE WAS STRUCK BY THE LOADER. LOTO WAS NOT APPLIED.") == "Employee was struck by the loader. LOTO was not applied."
    assert _lang("Worker confined space me bina gas testing ke ghus gaya") == "hinglish"
    assert _lang("The employee was struck by the falling pipe on the rig floor") == "english"
    assert _lang("LOTO नहीं किया") == "devanagari"
    assert _lang("Isolation kora nohol, panel ot kaam cholise.") == "assamese_roman"


def test_alert_outcome_and_language():
    from CLEANING.clean_alerts import (actual_fatality, choose_attachment_texts, iadc_reference, outcome_code,
                                       potential_consequence, strip_boilerplate, text_language)
    iadc = ("IADC Safety Alert\nALERT 06 \u2013 09\nDropped tong results in MTO\nWHAT HAPPENED:\n"
            "The tong swung and struck him on the shoulder. This could have resulted in a fatality had it struck his head.\n"
            "CORRECTIVE ACTIONS: To address this incident, this company issued the following to rig personnel:\nAdjust counterbalance.\n"
            "The Corrective Actions stated in this alert are one company's attempts to address the incident, and do not necessarily "
            "reflect the position of IADC or the IADC HSE Committee.")
    assert actual_fatality(iadc) is False                       # hedged "could have resulted in a fatality"
    assert actual_fatality("The worker fell 8 m and died at the scene.") is True
    assert actual_fatality("There was no fatality.") is False
    assert outcome_code("Dropped tong results in MTO") == "medical_treatment"
    assert outcome_code("Fall from stairs results in LTI") == "lost_time_injury"
    assert outcome_code("Fall from derrick results in fatality") == "fatality"
    assert outcome_code("Near miss: could have been a fatality") == "near_miss"
    assert iadc_reference(iadc) == ("06-09", 2006) and iadc_reference("Safety Alert No. 98-12")[1] == 1998
    st = strip_boilerplate(iadc)
    assert "issued the following" not in st and "IADC HSE Committee" not in st and "Adjust counterbalance" in st
    assert potential_consequence(iadc).startswith("This could have resulted in a fatality")
    es = "El trabajador estaba en la plataforma y fue golpeado por la tenaza. No se realiz\u00f3 el an\u00e1lisis de seguridad para la tarea."
    hi = "\u0915\u0930\u094d\u092e\u091a\u093e\u0930\u0940 \u092c\u093f\u0928\u093e \u0939\u093e\u0930\u094d\u0928\u0947\u0938 \u0915\u0947 \u090a\u0901\u091a\u093e\u0908 \u092a\u0930 \u0915\u093e\u092e \u0915\u0930 \u0930\u0939\u093e \u0925\u093e \u0914\u0930 \u0917\u093f\u0930 \u0917\u092f\u093e\u0964 \u0915\u094b\u0908 \u091a\u094b\u091f \u0928\u0939\u0940\u0902 \u0906\u0908\u0964"
    assert (text_language(iadc), text_language(es), text_language(hi)) == ("en", "es", "hi")
    en_t, hi_t, info = choose_attachment_texts([("a.pdf", iadc), ("a_spanish.pdf", es), ("a_hindi.pdf", hi)])
    assert "tong swung" in en_t and "trabajador" not in en_t and hi_t and [l["lang"] for l in info["languages"]] == ["en", "es", "hi"]


def test_oisd_header():
    from CLEANING.clean_alerts import oisd_header, strip_boilerplate
    head = ("SAFETY ALERT\nOISD/SA/2026-27/E&P/02 Date: 08.04.2026\nTitle: Fatal Accident while stacking Drill Pipe\n"
            "Location: Onshore Drilling Rig\nLoss/ Outcome: One Fatality\nINCIDENT\nAt drilling rig ...\n"
            "Provided for information purpose only. This information should be evaluated to determine if it is applicable in your\n"
            "operations, to avoid recurrence of such incidents.\nPage 1 of 3\nmore text")
    h = oisd_header(head)
    assert h["reference"] == "OISD/SA/2026-27/E&P/02" and h["date"] == "2026-04-08" and h["year"] == 2026
    assert h["title"].startswith("Fatal Accident") and h["location"] == "Onshore Drilling Rig" and h["actual_outcome"] == "fatality"
    assert h["segment"] == "exploration_production"
    st = strip_boilerplate(head)
    assert "Provided for information" not in st and "Page 1 of 3" not in st and "more text" in st


if __name__ == "__main__":
    failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"ok   {name}")
            except AssertionError as exc:
                failed += 1
                print(f"FAIL {name}: {exc!r}")
    raise SystemExit(1 if failed else 0)
