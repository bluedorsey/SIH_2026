"""
FastAPI dependency functions — DB session, pagination, common filters.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import Depends, Query
from sqlalchemy.orm import Session

from SERVER.DB.session import get_db_dependency
from SERVER.API.config import get_settings


#  DB session dependency 

def db_session():
    """Yield a per-request DB session (auto-commit / rollback)."""
    yield from get_db_dependency()


#  Pagination 

class PaginationParams:
    """Query-string pagination parsed into .page / .page_size / .offset."""

    def __init__(
        self,
        page: int = Query(1, ge=1, description="Page number (1-indexed)"),
        page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    ):
        settings = get_settings()
        self.page = page
        self.page_size = min(page_size, settings.max_page_size)
        self.offset = (self.page - 1) * self.page_size


#  Common filters (reused across queue, reports, patterns, sites) ─

class CommonFilters:
    """Standard query-string filters shared by list endpoints."""

    def __init__(
        self,
        site: Optional[str] = Query(None, description="Filter by site_code"),
        lsr: Optional[str] = Query(None, description="Filter by LSR code"),
        verdict: Optional[str] = Query(None, description="Filter by verdict label"),
        from_date: Optional[date] = Query(None, alias="from", description="Start date (inclusive)"),
        to_date: Optional[date] = Query(None, alias="to", description="End date (inclusive)"),
    ):
        self.site = site
        self.lsr = lsr
        self.verdict = verdict
        self.from_date = from_date
        self.to_date = to_date
