from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.engine import Connection

from SERVER.API.deps import db_session, PaginationParams, CommonFilters
from SERVER.API.services import site_svc

router = APIRouter(tags=["sites"])

@router.get("/")
def list_sites(
    db: Connection = Depends(db_session),
    filters: CommonFilters = Depends(),
    pagination: PaginationParams = Depends()
):
    results, total = site_svc.list_sites(
        db,
        filters={},
        pagination={"limit": pagination.page_size, "offset": pagination.offset}
    )
    return {"data": results, "total": total}

@router.get("/{site_code}")
def get_site_detail(site_code: str, db: Connection = Depends(db_session)):
    detail = site_svc.get_site_detail(db, site_code)
    if not detail:
        raise HTTPException(status_code=404, detail="Site not found")
    return detail
