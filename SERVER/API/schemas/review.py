from __future__ import annotations
from pydantic import BaseModel, ConfigDict

class ApproveRequest(BaseModel):
    reviewer_id: str
    note: str | None = None

class CorrectRequest(BaseModel):
    reviewer_id: str
    corrected_verdict: str
    corrected_lsr: list[str] | None = None
    note: str | None = None

class EscalateRequest(BaseModel):
    reviewer_id: str
    note: str | None = None

class ReviewLogEntry(BaseModel):
    action_id: str
    verdict_id: str
    report_id: str | None = None
    reviewer_id: str
    action: str
    corrected_verdict: str | None = None
    note: str | None = None
    acted_at: str
    original_verdict: str | None = None
    
    model_config = ConfigDict(from_attributes=True)

class AgreementStats(BaseModel):
    total_reviewed: int
    agreed: int
    disagreed: int
    agreement_rate: float
    by_verdict: dict[str, dict]
