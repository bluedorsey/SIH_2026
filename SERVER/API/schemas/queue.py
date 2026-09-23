from __future__ import annotations
from pydantic import BaseModel, ConfigDict

class QueueItem(BaseModel):
    verdict_id: str
    report_id: str
    raw_text: str
    verdict: str
    confidence: float | None = None
    lsr_primary: str | None = None
    hazard: str | None = None
    barrier_status: str | None = None
    site_code: str | None = None
    produced_at: str
    review_required: bool
    
    model_config = ConfigDict(from_attributes=True)

class QueueCounts(BaseModel):
    high: int
    medium: int
    low: int
    insufficient: int
