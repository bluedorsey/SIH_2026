from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.engine import Connection
from pydantic import BaseModel
from typing import Any
import io
import csv

from SERVER.API.deps import db_session
from SERVER.API.services import ingest_svc

router = APIRouter(tags=["ingest"])

class SingleReportRequest(BaseModel):
    text: str
    source: str
    site_code: str
    meta_data: dict[str, Any]
    report_id: str

@router.post("/report", status_code=202)
def ingest_report(req: SingleReportRequest, db: Connection = Depends(db_session)):
    try:
        return ingest_svc.ingest_single_report(
            db,
            req.text,
            req.source,
            req.site_code,
            req.meta_data,
            req.report_id
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

@router.post("/csv")
def ingest_csv(file: UploadFile = File(...), db: Connection = Depends(db_session)):
    content = file.file.read()
    rows = None

    # Try pandas first (best Excel/CSV support), fall back to stdlib csv
    try:
        import pandas as pd
        try:
            df = pd.read_csv(io.BytesIO(content))
        except Exception:
            try:
                df = pd.read_excel(io.BytesIO(content))
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid file format")
        rows = df.to_dict(orient='records')
    except ImportError:
        # pandas not available — use stdlib csv
        try:
            text = content.decode("utf-8")
            reader = csv.DictReader(io.StringIO(text))
            rows = list(reader)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid CSV format (pandas unavailable, only CSV supported)")

    return ingest_svc.ingest_csv_batch(db, rows)

@router.get("/jobs/{job_id}")
def get_job_status(job_id: str):
    return {"job_id": job_id, "status": "completed"}
