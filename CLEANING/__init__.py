"""SIH_26 raw-data cleaning pipeline. Run with `python -m CLEANING.run_pipeline` from the repo root."""

import sys as _sys

# Windows consoles default to cp1252 - Hindi/Assamese rows or arrows in reports would crash a print/log call.
for _stream in (_sys.stdout, _sys.stderr):
    try:
        if _stream and hasattr(_stream, "reconfigure") and (_stream.encoding or "").lower().replace("-", "") != "utf8":
            _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
