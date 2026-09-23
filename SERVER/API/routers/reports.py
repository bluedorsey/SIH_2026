from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.engine import Connection

from SERVER.API.deps import db_session, PaginationParams, CommonFilters
from SERVER.API.services import report_svc

router = APIRouter(tags=["reports"])

@router.get("/")
def list_reports(
    db: Connection = Depends(db_session),
    filters: CommonFilters = Depends(),
    pagination: PaginationParams = Depends()
):
    results, total = report_svc.list_reports(
        db,
        filters={"site_code": filters.site},
        pagination={"limit": pagination.page_size, "offset": pagination.offset}
    )
    return {"data": results, "total": total}

@router.get("/{report_id}")
def get_report_detail(report_id: str, db: Connection = Depends(db_session)):
    detail = report_svc.get_report_detail(db, report_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Report not found")
    return detail

@router.post("/{report_id}/reprocess")
def reprocess_report(report_id: str, db: Connection = Depends(db_session)):
    try:
        return report_svc.reprocess_report(db, report_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
