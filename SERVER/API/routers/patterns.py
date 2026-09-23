from fastapi import APIRouter, Depends
from sqlalchemy.engine import Connection

from SERVER.API.deps import db_session, PaginationParams, CommonFilters
from SERVER.API.services import pattern_svc

router = APIRouter(tags=["patterns"])

@router.get("/")
def list_patterns(
    db: Connection = Depends(db_session),
    filters: CommonFilters = Depends(),
    pagination: PaginationParams = Depends()
):
    results, total = pattern_svc.list_patterns(
        db,
        filters={},
        pagination={"limit": pagination.page_size, "offset": pagination.offset}
    )
    return {"data": results, "total": total}

@router.get("/{code}")
def get_pattern_detail(code: str):
    return pattern_svc.get_pattern_detail(code, "")

@router.get("/{code}/reports")
def get_pattern_reports(
    code: str,
    db: Connection = Depends(db_session),
    pagination: PaginationParams = Depends()
):
    results, total = pattern_svc.get_pattern_reports(
        db,
        code,
        pagination={"limit": pagination.page_size, "offset": pagination.offset}
    )
    return {"data": results, "total": total}
