"""
MSHA Accident Injuries data set -> DATA/RAW/MSHA/Accidents.txt

Source: https://arlweb.msha.gov/opengovernmentdata/ogimsha.asp  (US public domain, updated weekly)
Direct: https://arlweb.msha.gov/opengovernmentdata/DataSets/Accidents.zip  (~60-90 MB)
"""
from __future__ import annotations

import logging
import sys
import zipfile
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "CLEANING.fetch"  # noqa: A001

from ..config import RAW_MSHA_DIR  # noqa: E402
from ._http import download  # noqa: E402

log = logging.getLogger("fetch.msha")
ZIP_URL = "https://arlweb.msha.gov/opengovernmentdata/DataSets/Accidents.zip"
DEF_URL = "https://arlweb.msha.gov/OpenGovernmentData/DataSets/Accidents_Definition_File.txt"


def run(out_dir: Path = RAW_MSHA_DIR) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    download(DEF_URL, out_dir / "Accidents_Definition_File.txt")
    z = download(ZIP_URL, out_dir / "Accidents.zip")
    with zipfile.ZipFile(z) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith(".txt")]
        if not names:
            raise SystemExit(f"no .txt inside {z}: {zf.namelist()}")
        zf.extract(names[0], out_dir)
        src = out_dir / names[0]
        dest = out_dir / "Accidents.txt"
        if src != dest:
            src.replace(dest)
    log.info("MSHA ready: %s (%.0f MB)", dest, dest.stat().st_size / 1e6)
    return dest


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(name)s: %(message)s")
    run()
