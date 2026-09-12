"""HTTP service:

    pip install fastapi uvicorn
    uvicorn INFERENCE.api:app --host 0.0.0.0 --port 8000

    POST /analyse   {"text": "...", "report_id": "...", "meta": {...}}
    POST /batch     {"items": [{"text": "..."}, ...]}     (max 200)
    GET  /health    which layers are live
"""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from . import __version__
from .config import PIPELINE_VERSION
from .models import get_extractor, get_heads
from .pipeline import analyse

app = FastAPI(title="SIH26165 SIF precursor engine", version=PIPELINE_VERSION)


class Report(BaseModel):
    text: str = Field(min_length=3)
    report_id: str | None = None
    meta: dict[str, Any] | None = None


class Batch(BaseModel):
    items: list[Report] = Field(max_length=200)


@app.on_event("startup")
def _warm() -> None:
    get_extractor()          # load once, not on the first request
    get_heads()


@app.get("/health")
def health() -> dict:
    ex, hd = get_extractor(), get_heads()
    return {"status": "ok", "pipeline_version": PIPELINE_VERSION, "package_version": __version__,
            "layers": {"rules": True, "gliner": ex.available, "heads": hd.available},
            "gliner_source": ex.source, "heads": hd.names}


@app.post("/analyse")
def analyse_one(r: Report) -> dict:
    try:
        return analyse(r.text, report_id=r.report_id, meta=r.meta)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/batch")
def analyse_batch(b: Batch) -> dict:
    out = []
    for r in b.items:
        try:
            out.append(analyse(r.text, report_id=r.report_id, meta=r.meta))
        except ValueError as exc:
            out.append({"error": str(exc), "report_id": r.report_id})
    return {"count": len(out), "results": out}
