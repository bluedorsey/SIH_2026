"""
Central configuration for the SIH_26 data-cleaning pipeline.

Everything path-related is resolved relative to the repository root
(the parent of this CLEANING folder), so the pipeline works no matter
which drive/folder the repo is checked out to.
"""
from __future__ import annotations

from pathlib import Path

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------
CLEANING_DIR = Path(__file__).resolve().parent
REPO_ROOT = CLEANING_DIR.parent
DATA_DIR = REPO_ROOT / "DATA"
RAW_DIR = DATA_DIR / "RAW"
PROCESSED_DIR = DATA_DIR / "Processed"

RAW_IOGP_DIR = RAW_DIR / "IOGP_HiPo fatal"
RAW_OSHA_CSV = RAW_DIR / "OSHA Severe Injury Reports" / "January2015toNovember2025.csv"
RAW_REGISTER_DIR = RAW_DIR / "Register-style logs"
RAW_TERMS_JSON = RAW_DIR / "terms" / "terms.json"

OUT_IOGP_DIR = PROCESSED_DIR / "iogp"
OUT_OSHA_DIR = PROCESSED_DIR / "osha"
OUT_REGISTER_DIR = PROCESSED_DIR / "register"
OUT_TERMS_DIR = PROCESSED_DIR / "terms"
OUT_UNIFIED_DIR = PROCESSED_DIR / "unified"
OUT_REPORT_MD = PROCESSED_DIR / "quality_report.md"
OUT_MANIFEST_JSON = PROCESSED_DIR / "manifest.json"

# --------------------------------------------------------------------------
# IOGP PDF handling
# --------------------------------------------------------------------------
# File-name suffix -> record type.  Anything that does not match is a
# statistics / executive-summary report and is skipped (it has no narratives).
IOGP_SUFFIX_TO_TYPE = {
    "sf": "fatal",                   # "Fatal incident reports"
    "sh": "hipo",                    # "High potential event reports"
    "fpi": "permanent_impairment",   # "Permanent impairment incident reports"
}

# Regional section headings that appear as ALL-CAPS lines between records.
IOGP_REGIONS = {
    "AFRICA ONSHORE", "AFRICA OFFSHORE",
    "ASIA/AUSTRALASIA ONSHORE", "ASIA/AUSTRALASIA OFFSHORE",
    "EUROPE ONSHORE", "EUROPE OFFSHORE",
    "MIDDLE EAST ONSHORE", "MIDDLE EAST OFFSHORE",
    "NORTH AMERICA ONSHORE", "NORTH AMERICA OFFSHORE",
    "RUSSIA & CENTRAL ASIA ONSHORE", "RUSSIA & CENTRAL ASIA OFFSHORE",
    "SOUTH & CENTRAL AMERICA ONSHORE", "SOUTH & CENTRAL AMERICA OFFSHORE",
}

# Single-line metadata labels (label -> canonical field name).
IOGP_META_LABELS = {
    "DATE": "date_raw",
    "COUNTRY": "country",
    "NUMBER OF DEATHS": "number_of_deaths",
    "WORKFORCE DEATHS": "number_of_deaths",
    "NUMBER OF PERMANENT IMPAIRMENT INJURIES": "number_of_pi_injuries",
    "WORKFORCE PI INJURIES": "number_of_pi_injuries",
    "FUNCTION": "function",
    "CAUSE": "cause",
    "ACTIVITY": "activity",
    "RULE": "lsr_primary_raw",                     # 2022 layout (single rule)
    "PRIMARY LIFE-SAVING RULE": "lsr_primary_raw",
    "SECONARY LIFE-SAVING RULE": "lsr_secondary_raw",   # sic - typo in IOGP PDFs
    "SECONDARY LIFE-SAVING RULE": "lsr_secondary_raw",
    "SECONDARY LIFE-SAVING RULES": "lsr_secondary_raw",
}

# Multi-line section labels (label -> canonical field name).
IOGP_SECTION_LABELS = {
    "NARRATIVE": "narrative",
    "WHAT WENT WRONG": "what_went_wrong",
    "CORRECTIVE ACTIONS AND RECOMMENDATIONS": "corrective_actions",
    "CAUSAL FACTORS": "causal_factors_raw",
}

# Block headers that introduce the victim-detail block (no value of their own).
IOGP_VICTIM_BLOCK_HEADERS = {
    "FATALITY", "WORKFORCE FATALITY", "PERMANENT IMPAIRMENT", "WORKFORCE PERMANENT IMPAIRMENT",
}

# Sub-fields inside the victim-detail block.
IOGP_VICTIM_FIELDS = {
    "Function": "victim_function",
    "Employer": "victim_employer",
    "Occupation": "victim_occupation",
    "Body part": "victim_body_part",
    "Nature of injury": "victim_nature_of_injury",
    "Time in service": "victim_time_in_service",
    "PI Category": "pi_category",
    "PI Subcategory": "pi_subcategory",
    "LWDC Days": "lwdc_days",
    "RWDC Days": "rwdc_days",
}

# --------------------------------------------------------------------------
# IOGP Life-Saving Rules - canonical names + aliases
# --------------------------------------------------------------------------
LSR_CANONICAL = [
    "Bypassing Safety Controls",
    "Confined Space",
    "Driving",
    "Energy Isolation",
    "Hot Work",
    "Line of Fire",
    "Safe Mechanical Lifting",
    "Work Authorisation",
    "Working at Height",
]

# values IOGP uses to say "no rule applies" - mapped to None, NOT flagged as unmapped
LSR_NO_RULE_VALUES = {
    "null", "none", "n/a", "na", "-", "nil", "", "unspecified", "other", "not applicable",
    "other issue - no applicable rule", "other issue no applicable rule", "no applicable rule",
    "no rule", "no life-saving rule", "unspecified - other",
}

# lower-cased alias -> canonical
LSR_ALIASES = {
    "bypassing safety controls": "Bypassing Safety Controls",
    "bypass safety controls": "Bypassing Safety Controls",
    "confined space": "Confined Space",
    "confined spaces": "Confined Space",
    "confined space entry": "Confined Space",
    "driving": "Driving",
    "safe driving": "Driving",
    "energy isolation": "Energy Isolation",
    "isolation": "Energy Isolation",
    "loto": "Energy Isolation",
    "hot work": "Hot Work",
    "line of fire": "Line of Fire",
    "safe mechanical lifting": "Safe Mechanical Lifting",
    "mechanical lifting": "Safe Mechanical Lifting",
    "lifting operations": "Safe Mechanical Lifting",
    "lifting": "Safe Mechanical Lifting",
    "work authorisation": "Work Authorisation",
    "work authorization": "Work Authorisation",
    "permit to work": "Work Authorisation",
    "working at height": "Working at Height",
    "work at height": "Working at Height",
    "working at heights": "Working at Height",
}

# --------------------------------------------------------------------------
# OSHA Severe Injury Reports
# --------------------------------------------------------------------------
# NAICS prefixes that define the oil & gas contrast set
# 211    = Oil and Gas Extraction
# 213111 = Drilling Oil and Gas Wells
# 213112 = Support Activities for Oil and Gas Operations
# 324110 = Petroleum Refineries
OSHA_OILGAS_NAICS_PREFIXES = ("211", "213111", "213112", "324110")

# Raw column -> clean column
OSHA_COLUMNS = {
    "ID": "osha_id",
    "UPA": "upa",
    "EventDate": "event_date_raw",
    "Employer": "employer",
    "City": "city",
    "State": "state",
    "Primary NAICS": "naics",
    "Hospitalized": "hospitalized",
    "Amputation": "amputation",
    "Loss of Eye": "loss_of_eye",
    "Final Narrative": "narrative",
    "NatureTitle": "nature",
    "Part of Body Title": "part_of_body",
    "EventTitle": "event_type",
    "SourceTitle": "source",
    "Secondary Source Title": "secondary_source",
}

# --------------------------------------------------------------------------
# Register-style logs (near-miss / UA-UC registers)
# --------------------------------------------------------------------------
# canonical column -> list of lower-cased header fragments that map to it.
# Matching is "fragment in header" after lower-casing and stripping punctuation.
REGISTER_COLUMN_MAP = {
    "sno": ["s/no", "sno", "s.no", "sl no", "sr no", "serial", "#"],
    "date": ["date"],
    "shift": ["shift"],
    "time_of_day": ["day/night", "time (day", "day night", "time of day"],
    "description": ["description", "observation)", "near miss description", "unsafe act/condition", "details"],
    "category": ["category"],
    "sub_category": ["near miss observation", "sub category", "subcategory", "type"],
    "area": ["area", "location"],
    "observer": ["raised by", "observer", "reported by", "reporter"],
    "status": ["status"],
    "corrective_action": ["corrective", "follow up", "action taken", "recommendation"],
    "comments": ["comment", "remarks"],
    "department": ["department", "dept"],
    "unit": ["unit"],
    "sub_location": ["sub-location", "sub location", "sublocation"],
}

# Category normalisation: lower-cased raw -> UA / UC / NM / INC
REGISTER_CATEGORY_MAP = {
    "unsafe act": "UA",
    "ua": "UA",
    "unsafe condition": "UC",
    "uc": "UC",
    "near miss": "NM",
    "near-miss": "NM",
    "nm": "NM",
    "incident": "INC",
    "accident": "INC",
}

# --------------------------------------------------------------------------
# terms.json glossary
# --------------------------------------------------------------------------
# safety_signal values used in the raw glossary -> GLiNER role names (prompts.md §0)
TERMS_SIGNAL_MAP = {
    "energy_cue": "energy_cue",
    "release_cue": "release_cue",
    "no_release_cue": "no_release_cue",
    "exposure_cue": "exposure_cue",
    "control_present": "control_present",
    "control_absent": "control_absent",
    "control_ineffective": "control_ineffective",
    "pseudo_control": "pseudo_control",
    "negation_cue": "negation_cue",
    "outcome_cue": "outcome_cue",
    "outcome": "outcome_cue",
    "statement_cue": "statement_cue",
    "statement_type": "statement_cue",
    "none": None,
    "": None,
}

# --------------------------------------------------------------------------
# Deduplication
# --------------------------------------------------------------------------
NEAR_DUP_JACCARD_THRESHOLD = 0.85   # word-3-gram MinHash similarity above which two texts are "near duplicates"
MINHASH_NUM_PERM = 64
MIN_TEXT_CHARS = 15                  # texts shorter than this are dropped as unusable
