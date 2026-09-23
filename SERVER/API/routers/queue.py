from fastapi import APIRouter, Depends
from sqlalchemy.engine import Connection
from typing import Any

from SERVER.API.deps import db_session, PaginationParams, CommonFilters
from SERVER.API.services import queue_svc

router = APIRouter(tags=["queue"])

@router.get("/")
def get_queue(
    db: Connection = Depends(db_session),
    filters: CommonFilters = Depends(),
    pagination: PaginationParams = Depends()
):
    results, total = queue_svc.get_queue(
        db, 
        filters={"site_code": filters.site, "lsr": filters.lsr, "verdict": filters.verdict}, 
        pagination={"limit": pagination.page_size, "offset": pagination.offset}
    )
    return {"data": results, "total": total}

@router.get("/counts")
def get_queue_counts(db: Connection = Depends(db_session)):
    return queue_svc.get_queue_counts(db)
