from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, ConfigDict

class PrecursorRollup(BaseModel):
    code: str
    display_name: str
    report_count: int
    sif_weighted_count: float
    sites_affected: int
    trend_direction: Literal["up", "down", "stable"]

class PRRData(BaseModel):
    prr: float
    ci_lower: float
    ci_upper: float
    a: int
    b: int
    c: int
    d: int
    flagged: bool

class CUSUMPoint(BaseModel):
    period: str
    count: int
    cusum: float
    baseline_mean: float
    flagged: bool

class PrecursorDrilldown(BaseModel):
    code: str
    display_name: str
    report_count: int
    prr: PRRData | None = None
    cusum_series: list[CUSUMPoint] = []
    site_breakdown: list[dict] = []
