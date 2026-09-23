from fastapi import APIRouter, Depends
from sqlalchemy.engine import Connection
from pydantic import BaseModel
from typing import Optional, List

from SERVER.API.deps import db_session, PaginationParams
from SERVER.API.services import review_svc

router = APIRouter(tags=["review"])

class ReviewNote(BaseModel):
    reviewer_id: str
    note: Optional[str] = ""

class CorrectNote(ReviewNote):
    corrected_verdict: str
    corrected_lsr: Optional[List[str]] = None

@router.post("/{verdict_id}/approve")
def approve_verdict(verdict_id: str, req: ReviewNote, db: Connection = Depends(db_session)):
    return review_svc.approve_verdict(db, verdict_id, req.reviewer_id, req.note)

@router.post("/{verdict_id}/correct")
def correct_verdict(verdict_id: str, req: CorrectNote, db: Connection = Depends(db_session)):
    return review_svc.correct_verdict(db, verdict_id, req.reviewer_id, req.corrected_verdict, req.corrected_lsr, req.note)

@router.post("/{verdict_id}/escalate")
def escalate_verdict(verdict_id: str, req: ReviewNote, db: Connection = Depends(db_session)):
    return review_svc.escalate_verdict(db, verdict_id, req.reviewer_id, req.note)

@router.get("/log")
def get_review_log(db: Connection = Depends(db_session), pagination: PaginationParams = Depends()):
    results, total = review_svc.get_review_log(db, {"limit": pagination.page_size, "offset": pagination.offset})
    return {"data": results, "total": total}

@router.get("/agreement")
def get_agreement_stats(db: Connection = Depends(db_session)):
    return review_svc.get_agreement_stats(db)
