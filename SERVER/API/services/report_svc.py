from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.engine import Connection

from SERVER.DB.models import reports, verdicts, spans, actions

def get_report_detail(session: Connection, report_id: str) -> dict | None:
    rep = session.execute(sa.select(reports).where(reports.c.report_id == report_id)).mappings().first()
    if not rep:
        return None
        
    verdict = session.execute(
        sa.select(verdicts).where(verdicts.c.report_id == report_id, verdicts.c.is_current == True)
    ).mappings().first()
    
    span_list = []
    action_list = []
    
    if verdict:
        span_list = [dict(r) for r in session.execute(
            sa.select(spans).where(spans.c.verdict_id == verdict["verdict_id"])
        ).mappings().all()]
        
        action_list = [dict(r) for r in session.execute(
            sa.select(actions).where(actions.c.verdict_id == verdict["verdict_id"])
        ).mappings().all()]
        
    return {
        "report": dict(rep),
        "verdict": dict(verdict) if verdict else None,
        "spans": span_list,
        "review_history": action_list
    }

def list_reports(session: Connection, filters: dict, pagination: dict) -> tuple[list, int]:
    stmt = sa.select(
        reports.c.report_id,
        reports.c.site_code,
        reports.c.ingested_at,
        reports.c.raw_text,
        reports.c.metadata,
        verdicts.c.verdict,
        verdicts.c.lsr_primary
    ).select_from(
        reports.outerjoin(verdicts, sa.and_(reports.c.report_id == verdicts.c.report_id, verdicts.c.is_current == True))
    )
    
    if filters.get("site_code"):
        stmt = stmt.where(reports.c.site_code == filters["site_code"])
        
    # Count total
    count_stmt = sa.select(sa.func.count()).select_from(stmt.subquery())
    total = session.execute(count_stmt).scalar()
    
    limit = pagination.get("limit", 20)
    offset = pagination.get("offset", 0)
    stmt = stmt.limit(limit).offset(offset).order_by(reports.c.ingested_at.desc())
    
    results = [dict(r) for r in session.execute(stmt).mappings()]
    return results, total

def reprocess_report(session: Connection, report_id: str) -> dict:
    from SERVER.API.services.ingest_svc import ingest_single_report
    rep = session.execute(sa.select(reports).where(reports.c.report_id == report_id)).mappings().first()
    if not rep:
        raise ValueError(f"Report {report_id} not found")
        
    # Set old verdict to not current
    session.execute(
        sa.update(verdicts)
        .where(verdicts.c.report_id == report_id, verdicts.c.is_current == True)
        .values(is_current=False)
    )
    
    # Ingest again
    return ingest_single_report(
        session,
        rep["raw_text"],
        rep["source"],
        rep["site_code"],
        rep["meta_data"],
        report_id
    )
