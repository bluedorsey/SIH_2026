"""Production inference for SIH26165 - SIF precursor detection.

Standalone: never imports CLEANING or TRAINING. Everything it needs at run time is
the tuned model folders plus this package.
"""
import sys

if sys.platform == "win32":                       # keep Devanagari/Assamese readable in a console
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8")
        except Exception:                          # noqa: BLE001
            pass

__version__ = "0.7.0"
