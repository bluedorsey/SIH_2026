from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class IngestReportRequest(BaseModel):
    text: str = Field(min_length=3)
    source: str = "api_ingest"
    site_code: str | None = None
    meta: dict | None = None
    report_id: str | None = None

class IngestCSVResponse(BaseModel):
    job_id: str
    total_rows: int
    status: str = "pending"

class JobStatusResponse(BaseModel):
    job_id: str
    status: Literal["pending", "running", "done", "failed"]
    rows_processed: int
    rows_failed: int
    errors: list[str]
