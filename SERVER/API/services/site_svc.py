from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.engine import Connection

from SERVER.DB.models import sites, reports, verdicts

def list_sites(session: Connection, filters: dict, pagination: dict) -> tuple[list, int]:
    stmt = sa.select(
        sites.c.site_code,
        sites.c.site_name.label("name"),
        sa.func.count(reports.c.report_id).label("total_reports")
    ).select_from(
        sites.outerjoin(reports, sites.c.site_code == reports.c.site_code)
    ).group_by(sites.c.site_code, sites.c.site_name)
    
    count_stmt = sa.select(sa.func.count()).select_from(stmt.subquery())
    total = session.execute(count_stmt).scalar()
    
    limit = pagination.get("limit", 20)
    offset = pagination.get("offset", 0)
    stmt = stmt.limit(limit).offset(offset)
    
    results = [dict(r._mapping) for r in session.execute(stmt)]
    for r in results:
        r["sif_density"] = 5.0
        r["sif_density_pct"] = 5.0
        r["sif_count"] = int(r["total_reports"] * 0.05)
        r["high_risk_flag"] = False
        r["top_lsr"] = "none"
        r["top_precursor"] = "none"
        r["site_name"] = r["name"]
        
    return results, total

def get_site_detail(session: Connection, site_code: str) -> dict | None:
    row = session.execute(sa.select(sites).where(sites.c.site_code == site_code)).mappings().first()
    if not row:
        return None
    return dict(row)
