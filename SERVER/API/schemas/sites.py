from __future__ import annotations
from pydantic import BaseModel, ConfigDict

class SiteRollup(BaseModel):
    site_code: str
    site_name: str
    region: str | None = None
    total_reports: int
    sif_density_pct: float
    high_risk: bool
    top_lsr: str | None = None
    top_precursor: str | None = None

class SiteDrilldown(BaseModel):
    site_code: str
    site_name: str
    region: str | None = None
    site_type: str | None = None
    total_reports: int
    sif_density_pct: float
    activity_breakdown: list[dict] = []
    barrier_breakdown: list[dict] = []
    cusum_data: list[dict] = []
    recent_reports: list[dict] = []
