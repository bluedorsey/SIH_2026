from __future__ import annotations

import os
import logging
import duckdb

logger = logging.getLogger(__name__)

def _get_duckdb_path(path: str | None = None) -> str:
    if path is not None:
        return path
    return os.getenv("DUCKDB_PATH", "SERVER/ANALYTICS/oilens_analytics.duckdb")

def barrier_health(hazard: str | None = None, site_code: str | None = None, duckdb_path: str | None = None) -> list[dict]:
    """Computes barrier health rollups."""
    db_path = _get_duckdb_path(duckdb_path)
    if not os.path.exists(db_path):
        logger.warning(f"DuckDB path {db_path} does not exist.")
        return []

    try:
        with duckdb.connect(db_path, read_only=True) as con:
            query = """
                SELECT v.hazard, v.barrier, v.barrier_status, COUNT(*) as cnt
                FROM verdicts v
                JOIN reports r ON v.report_id = r.report_id
                WHERE v.hazard IS NOT NULL AND v.barrier IS NOT NULL AND v.barrier_status IS NOT NULL
            """
            
            params = []
            if hazard:
                query += " AND v.hazard = ?"
                params.append(hazard)
            if site_code:
                query += " AND r.site_code = ?"
                params.append(site_code)
                
            query += " GROUP BY v.hazard, v.barrier, v.barrier_status"
            
            data = con.execute(query, params).fetchall()
            
            groups = {}
            for haz, bar, status, cnt in data:
                key = (haz, bar)
                if key not in groups:
                    groups[key] = {"present": 0, "absent": 0, "ineffective": 0, "pseudo": 0}
                groups[key][status.lower()] = cnt
                
            results = []
            for (haz, bar), counts in groups.items():
                total = sum(counts.values())
                failures = counts.get("absent", 0) + counts.get("ineffective", 0) + counts.get("pseudo", 0)
                failure_rate = failures / total if total > 0 else 0.0
                results.append({
                    "hazard": haz,
                    "barrier": bar,
                    "status_counts": counts,
                    "total": total,
                    "failure_rate": failure_rate
                })
                
            return results
    except Exception as e:
        logger.error(f"Error computing barrier health: {e}")
        return []
