from __future__ import annotations
from pydantic import BaseModel, ConfigDict

class HealthResponse(BaseModel):
    status: str
    db_connected: bool
    models_loaded: bool
    pipeline_version: str
    queue_depth: int

class ModelInfo(BaseModel):
    name: str
    version: str | None = None
    model_type: str
    loaded: bool
    last_finetune: str | None = None

class ConfigResponse(BaseModel):
    thresholds: list[dict] = []
    pipeline_version: str
    scope_enabled: bool
    review_confidence_cutoff: float

class SyncStatus(BaseModel):
    last_sync: str | None = None
    pending_rows: int
    status: str
