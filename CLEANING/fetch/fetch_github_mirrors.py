"""
Public GitHub mirrors of two datasets (the only ones reachable from the sandbox).

1. IHM Stefanini industrial safety DB (Kaggle, CC0) - 425 rows with Accident Level vs Potential Accident Level
   -> DATA/RAW/Kaggle_IHM/IHMStefanini_industrial_safety_and_health_database_with_accidents_description.csv
2. OSHA fatality/catastrophe investigation summaries (IMIS abstracts, 2004-2013, 16,323 rows, keyword-tagged)
   plus the 4,470-case construction subset with cause / fatcause / diagnosis labels
   -> DATA/RAW/OSHA Accident Abstracts/*.xlsx
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "CLEANING.fetch"  # noqa: A001

from ..config import RAW_IHM_DIR, RAW_OSHA_ABSTRACTS_DIR  # noqa: E402
from ._http import download  # noqa: E402

log = logging.getLogger("fetch.github")

FILES = [
    ("https://raw.githubusercontent.com/aws-samples/amazon-sagemaker-sentence-similarity-hugging-face/main/IHMStefanini_industrial_safety_and_health_database_with_accidents_description.csv",
     RAW_IHM_DIR, "IHMStefanini_industrial_safety_and_health_database_with_accidents_description.csv"),
    ("https://raw.githubusercontent.com/safetyhub/OSHA_Acc/master/osha.xlsx",
     RAW_OSHA_ABSTRACTS_DIR, "osha_abstracts_16k.xlsx"),
    ("https://raw.githubusercontent.com/safetyhub/OSHA_Acc/master/osha%204470%20(with%20additional%20metadata%20scraped%20from%20narrative%20site).xlsx",
     RAW_OSHA_ABSTRACTS_DIR, "osha_construction_4470_metadata.xlsx"),
    ("https://raw.githubusercontent.com/safetyhub/OSHA_Acc/master/tagged1000.xlsx",
     RAW_OSHA_ABSTRACTS_DIR, "osha_construction_tagged1000.xlsx"),
]


def run() -> list[Path]:
    out = []
    for url, d, name in FILES:
        try:
            out.append(download(url, d / name, delay=0.5))
        except Exception as exc:  # noqa: BLE001
            log.error("failed %s: %s", name, exc)
    return out


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(name)s: %(message)s")
    run()
