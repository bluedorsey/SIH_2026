from __future__ import annotations

from datetime import datetime, timezone
import sqlalchemy as sa
from sqlalchemy.engine import Connection

from SERVER.DB.models import actions, verdicts

def approve_verdict(session: Connection, verdict_id: str, reviewer_id: str, note: str) -> dict:
    ins = sa.insert(actions).values(
        verdict_id=verdict_id,
        reviewer_id=reviewer_id,
        action='approve',
        note=note,
        acted_at=datetime.now(timezone.utc)
    ).returning(actions.c.action_id)
    action_id = session.execute(ins).scalar()
    return {"action_id": str(action_id), "status": "approved"}

def correct_verdict(session: Connection, verdict_id: str, reviewer_id: str, corrected_verdict: str, corrected_lsr: list | None, note: str) -> dict:
    ins = sa.insert(actions).values(
        verdict_id=verdict_id,
        reviewer_id=reviewer_id,
        action='correct',
        corrected_verdict=corrected_verdict,
        corrected_lsr=corrected_lsr,
        note=note,
        acted_at=datetime.now(timezone.utc)
    ).returning(actions.c.action_id)
    action_id = session.execute(ins).scalar()
    return {"action_id": str(action_id), "status": "corrected"}

def escalate_verdict(session: Connection, verdict_id: str, reviewer_id: str, note: str) -> dict:
    ins = sa.insert(actions).values(
        verdict_id=verdict_id,
        reviewer_id=reviewer_id,
        action='escalate',
        note=note,
        acted_at=datetime.now(timezone.utc)
    ).returning(actions.c.action_id)
    action_id = session.execute(ins).scalar()
    return {"action_id": str(action_id), "status": "escalated"}

def get_review_log(session: Connection, pagination: dict) -> tuple[list, int]:
    stmt = sa.select(actions)
    
    count_stmt = sa.select(sa.func.count()).select_from(actions)
    total = session.execute(count_stmt).scalar()
    
    limit = pagination.get("limit", 20)
    offset = pagination.get("offset", 0)
    stmt = stmt.limit(limit).offset(offset).order_by(actions.c.acted_at.desc())
    
    results = [dict(r) for r in session.execute(stmt).mappings()]
    return results, total

def get_agreement_stats(session: Connection) -> dict:
    # Real agreement stats from the database
    total = session.execute(sa.select(sa.func.count()).select_from(actions)).scalar() or 0
    agreed = session.execute(
        sa.select(sa.func.count()).select_from(actions).where(actions.c.action == 'approve')
    ).scalar() or 0
    disagreed = session.execute(
        sa.select(sa.func.count()).select_from(actions).where(actions.c.action == 'correct')
    ).scalar() or 0
    rate = round((agreed / total * 100), 1) if total > 0 else 0.0
    return {"agreement_rate": rate, "total_reviewed": total, "agreed": agreed, "disagreed": disagreed}
