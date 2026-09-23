from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.engine import Connection

from SERVER.DB.models import reports, verdicts, actions

def get_queue(session: Connection, filters: dict, pagination: dict) -> tuple[list, int]:
    # Query derived.verdicts WHERE review_required=True AND is_current=True
    # LEFT JOIN review.actions to exclude already-reviewed
    # WHERE review.actions.action_id IS NULL
    
    stmt = sa.select(
        verdicts.c.verdict_id,
        verdicts.c.report_id,
        verdicts.c.verdict,
        verdicts.c.confidence,
        verdicts.c.produced_at,
        reports.c.site_code,
        reports.c.raw_text,
        verdicts.c.lsr_primary,
        verdicts.c.activity,
        verdicts.c.barrier_status,
        verdicts.c.energy_detail
    ).select_from(
        verdicts.join(reports, verdicts.c.report_id == reports.c.report_id)
        .outerjoin(actions, verdicts.c.verdict_id == actions.c.verdict_id)
    ).where(
        verdicts.c.review_required == True,
        verdicts.c.is_current == True,
        actions.c.action_id == None
    )
    
    if filters.get("site_code"):
        stmt = stmt.where(reports.c.site_code == filters["site_code"])
    if filters.get("lsr"):
        stmt = stmt.where(verdicts.c.lsr_primary == filters["lsr"])
    if filters.get("verdict"):
        stmt = stmt.where(verdicts.c.verdict == filters["verdict"])
    
    # Sort by verdict severity then produced_at DESC
    # For now simply ordering by verdict, then produced_at
    stmt = stmt.order_by(verdicts.c.verdict.asc(), verdicts.c.produced_at.desc())
    
    # Count total
    count_stmt = sa.select(sa.func.count()).select_from(stmt.subquery())
    total = session.execute(count_stmt).scalar()
    
    # Paginate
    limit = pagination.get("limit", 20)
    offset = pagination.get("offset", 0)
    stmt = stmt.limit(limit).offset(offset)
    
    results = [dict(row._mapping) for row in session.execute(stmt)]
    return results, total

def get_queue_counts(session: Connection) -> dict:
    stmt = sa.select(verdicts.c.verdict, sa.func.count()).select_from(
        verdicts.outerjoin(actions, verdicts.c.verdict_id == actions.c.verdict_id)
    ).where(
        verdicts.c.review_required == True,
        verdicts.c.is_current == True,
        actions.c.action_id == None
    ).group_by(verdicts.c.verdict)
    
    counts = {row[0]: row[1] for row in session.execute(stmt)}
    
    high = counts.get('H_SIF', 0) + counts.get('P_SIF', 0)
    medium = counts.get('EXPOSURE', 0) + counts.get('CAPACITY', 0)
    low = counts.get('LOW_ENERGY', 0) + counts.get('NON_EVENT', 0) + counts.get('SUCCESS', 0)
    insufficient = counts.get('INSUFFICIENT', 0)
    
    return {
        "high": high,
        "medium": medium,
        "low": low,
        "insufficient": insufficient
    }
