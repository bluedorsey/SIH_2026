from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.engine import Connection

from SERVER.DB.models import precursors, precursor_links, verdicts, reports

def list_patterns(session: Connection, filters: dict, pagination: dict) -> tuple[list, int]:
    # Query reference.precursors with rollups
    stmt = sa.select(
        precursors.c.code,
        precursors.c.display_name.label("name"),
        sa.func.count(verdicts.c.verdict_id).label("report_count"),
        sa.func.count(sa.func.distinct(reports.c.site_code)).label("sites_affected")
    ).select_from(
        precursors
        .outerjoin(precursor_links, precursors.c.code == precursor_links.c.precursor_code)
        .outerjoin(verdicts, sa.and_(precursor_links.c.verdict_id == verdicts.c.verdict_id, verdicts.c.is_current == True))
        .outerjoin(reports, verdicts.c.report_id == reports.c.report_id)
    ).group_by(precursors.c.code, precursors.c.display_name)
    
    count_stmt = sa.select(sa.func.count()).select_from(stmt.subquery())
    total = session.execute(count_stmt).scalar()
    
    limit = pagination.get("limit", 20)
    offset = pagination.get("offset", 0)
    stmt = stmt.limit(limit).offset(offset)
    
    results = [dict(r._mapping) for r in session.execute(stmt)]
    for r in results:
        r["trend"] = "stable"  
        r["sif_weighted_count"] = r["report_count"] * 1.5 
        r["display_name"] = r["name"]
        
    return results, total

def get_pattern_detail(code: str, duckdb_path: str) -> dict:
    return {"code": code, "detail": "Analytics module stub"}

def get_pattern_reports(session: Connection, code: str, pagination: dict) -> tuple[list, int]:
    stmt = sa.select(
        reports.c.report_id,
        verdicts.c.verdict
    ).select_from(
        precursor_links
        .join(verdicts, sa.and_(precursor_links.c.verdict_id == verdicts.c.verdict_id, verdicts.c.is_current == True))
        .join(reports, verdicts.c.report_id == reports.c.report_id)
    ).where(precursor_links.c.precursor_code == code)
    
    count_stmt = sa.select(sa.func.count()).select_from(stmt.subquery())
    total = session.execute(count_stmt).scalar()
    
    limit = pagination.get("limit", 20)
    offset = pagination.get("offset", 0)
    stmt = stmt.limit(limit).offset(offset)
    
    results = [dict(r) for r in session.execute(stmt).mappings()]
    return results, total
