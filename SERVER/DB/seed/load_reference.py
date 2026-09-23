"""
Seed reference tables with demo data.

Run:  python -m SERVER.DB.seed.load_reference
"""
from __future__ import annotations

import os
import sys

# Ensure repo root is on sys.path when run directly
if __name__ == "__main__":
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from sqlalchemy.dialects.postgresql import insert
from SERVER.DB.session import get_engine, ensure_schemas
from SERVER.DB.models import life_saving_rules, precursors, sites, thresholds


def load_reference_data():
    engine = get_engine()
    ensure_schemas(engine)

    # ── Life Saving Rules (9) ────────────────────────────────────────────
    lsr_data = [
        {"code": "energy_isolation",          "display_name": "Energy Isolation",          "iogp_number": 1, "oil_internal_aliases": ["LOTO", "Isolation"]},
        {"code": "hot_work",                  "display_name": "Hot Work",                  "iogp_number": 2, "oil_internal_aliases": ["Hot Work Permit", "Welding Safety"]},
        {"code": "confined_space",            "display_name": "Confined Space",            "iogp_number": 3, "oil_internal_aliases": ["Confined Space Entry"]},
        {"code": "line_of_fire",              "display_name": "Line of Fire",              "iogp_number": 4, "oil_internal_aliases": ["Line of Fire"]},
        {"code": "work_at_height",            "display_name": "Working at Height",         "iogp_number": 5, "oil_internal_aliases": ["Height Work", "Scaffolding"]},
        {"code": "safe_mechanical_lifting",   "display_name": "Safe Mechanical Lifting",   "iogp_number": 6, "oil_internal_aliases": ["Crane Safety", "Lifting Operations"]},
        {"code": "driving",                   "display_name": "Driving",                   "iogp_number": 7, "oil_internal_aliases": ["Vehicle Safety", "Driving Safety"]},
        {"code": "bypassing_safety_controls", "display_name": "Bypassing Safety Controls", "iogp_number": 8, "oil_internal_aliases": ["Safety Override"]},
        {"code": "work_authorisation",        "display_name": "Work Authorisation",        "iogp_number": 9, "oil_internal_aliases": ["Permit to Work", "PTW"]},
    ]

    # ── Precursor Clusters (10) — matching INFERENCE/knowledge.py ────────
    precursor_data = [
        {"code": "DROPPED_OBJECT_NO_EXCLUSION_ZONE",  "display_name": "Dropped Object – No Exclusion Zone",  "lsr_code": "line_of_fire"},
        {"code": "WORK_AT_HEIGHT_NO_FALL_ARREST",     "display_name": "Work at Height – No Fall Arrest",     "lsr_code": "work_at_height"},
        {"code": "LIVE_WORK_NO_ISOLATION",             "display_name": "Live Work – No Energy Isolation",     "lsr_code": "energy_isolation"},
        {"code": "CONFINED_SPACE_NO_GAS_TEST",         "display_name": "Confined Space – No Gas Test",        "lsr_code": "confined_space"},
        {"code": "HOT_WORK_NO_PERMIT",                 "display_name": "Hot Work – No Permit",                "lsr_code": "hot_work"},
        {"code": "PRESSURISED_LINE_NOT_ISOLATED",      "display_name": "Pressurised Line – Not Isolated",     "lsr_code": "energy_isolation"},
        {"code": "ROTATING_EQUIPMENT_NO_GUARD",        "display_name": "Rotating Equipment – No Guard",       "lsr_code": "safe_mechanical_lifting"},
        {"code": "MOBILE_PLANT_NO_SEGREGATION",        "display_name": "Mobile Plant – No Segregation",       "lsr_code": "driving"},
        {"code": "SUSPENDED_LOAD_PERSON_UNDERNEATH",   "display_name": "Suspended Load – Person Underneath",  "lsr_code": "safe_mechanical_lifting"},
        {"code": "EXCAVATION_NO_SHORING",              "display_name": "Excavation – No Shoring",             "lsr_code": "line_of_fire"},
    ]

    # ── OIL India Sites (10) ─────────────────────────────────────────────
    site_data = [
        {"site_code": "DLJ", "site_name": "Duliajan",    "region": "Assam",            "site_type": "OCS"},
        {"site_code": "MRN", "site_name": "Moran",       "region": "Assam",            "site_type": "OCS"},
        {"site_code": "DGB", "site_name": "Digboi",      "region": "Assam",            "site_type": "GGS"},
        {"site_code": "JRT", "site_name": "Jorhat",      "region": "Assam",            "site_type": "CTF"},
        {"site_code": "NZR", "site_name": "Nazira",      "region": "Assam",            "site_type": "OCS"},
        {"site_code": "RDR", "site_name": "Rudrasagar",  "region": "Assam",            "site_type": "GGS"},
        {"site_code": "LKW", "site_name": "Lakwa",       "region": "Assam",            "site_type": "OCS"},
        {"site_code": "GLK", "site_name": "Geleki",      "region": "Assam",            "site_type": "GGS"},
        {"site_code": "KGB", "site_name": "KG Basin",    "region": "Andhra Pradesh",   "site_type": "OCS"},
        {"site_code": "RJN", "site_name": "Rajasthan",   "region": "Rajasthan",        "site_type": "drilling_rig"},
    ]

    # ── Thresholds (6) — from INFERENCE/config.py ────────────────────────
    threshold_data = [
        {"key": "energy.gravity_fall_m",     "value": 1.2,   "unit": "meters"},
        {"key": "energy.dropped_object_j",   "value": 680.0, "unit": "joules"},
        {"key": "energy.electrical_v",       "value": 50.0,  "unit": "volts"},
        {"key": "energy.temperature_c",      "value": 65.0,  "unit": "celsius"},
        {"key": "energy.excavation_depth_m", "value": 1.5,   "unit": "meters"},
        {"key": "energy.pressure_bar",       "value": 7.0,   "unit": "bar"},
    ]

    with engine.begin() as conn:
        print("Seeding Life Saving Rules...")
        stmt = insert(life_saving_rules).values(lsr_data)
        conn.execute(stmt.on_conflict_do_nothing(index_elements=["code"]))

        print("Seeding Precursor Clusters...")
        stmt = insert(precursors).values(precursor_data)
        conn.execute(stmt.on_conflict_do_nothing(index_elements=["code"]))

        print("Seeding Sites...")
        stmt = insert(sites).values(site_data)
        conn.execute(stmt.on_conflict_do_nothing(index_elements=["site_code"]))

        print("Seeding Thresholds...")
        stmt = insert(thresholds).values(threshold_data)
        conn.execute(stmt.on_conflict_do_nothing(index_elements=["key"]))

    print("Reference data loaded successfully.")


if __name__ == "__main__":
    load_reference_data()
