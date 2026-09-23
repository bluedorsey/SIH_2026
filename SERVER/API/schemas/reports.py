from __future__ import annotations
from pydantic import BaseModel, ConfigDict

class SpanDetail(BaseModel):
    span_id: str
    role: str
    text_span: str
    char_start: int | None = None
    char_end: int | None = None
    source: str
    score: float | None = None
    
    model_config = ConfigDict(from_attributes=True)

class VerdictDetail(BaseModel):
    verdict_id: str
    pipeline_version: str
    produced_at: str
    verdict: str
    confidence: float | None = None
    review_required: bool
    q1_high_energy: bool | None = None
    q2_energy_released: bool | None = None
    q3_person_exposed: bool | None = None
    q4_control_effective: bool | None = None
    lsr_primary: str | None = None
    lsr_secondary: list[str] | None = None
    activity: str | None = None
    hazard: str | None = None
    barrier: str | None = None
    barrier_status: str | None = None
    potential_consequence: str | None = None
    explanation: str | None = None
    is_current: bool
    energy_detail: dict | None = None
    uc_ua_detail: dict | None = None
    spans: list[SpanDetail] = []
    
    model_config = ConfigDict(from_attributes=True)

class ReviewAction(BaseModel):
    action_id: str
    reviewer_id: str
    action: str
    corrected_verdict: str | None = None
    corrected_lsr: list[str] | None = None
    note: str | None = None
    acted_at: str
    
    model_config = ConfigDict(from_attributes=True)

class ReportDetail(BaseModel):
    report_id: str
    source: str
    site_code: str | None = None
    raw_text: str
    ingested_at: str
    language_hint: str | None = None
    metadata: dict | None = None
    current_verdict: VerdictDetail | None = None
    review_history: list[ReviewAction] = []
    
    model_config = ConfigDict(from_attributes=True)

class ReportSummary(BaseModel):
    report_id: str
    source: str
    site_code: str | None = None
    verdict: str | None = None
    confidence: float | None = None
    lsr_primary: str | None = None
    ingested_at: str
    review_required: bool | None = None
    
    model_config = ConfigDict(from_attributes=True)

class ReprocessResponse(BaseModel):
    report_id: str
    new_verdict_id: str
    verdict: str
    confidence: float | None = None
