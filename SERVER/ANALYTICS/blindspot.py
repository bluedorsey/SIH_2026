from __future__ import annotations

import os
import math
import logging
import duckdb

logger = logging.getLogger(__name__)

def _get_duckdb_path(path: str | None = None) -> str:
    if path is not None:
        return path
    return os.getenv("DUCKDB_PATH", "SERVER/ANALYTICS/oilens_analytics.duckdb")

def detect_blindspots(duckdb_path: str | None = None) -> list[dict]:
    """Detects reporting blind spots for sites."""
    db_path = _get_duckdb_path(duckdb_path)
    if not os.path.exists(db_path):
        logger.warning(f"DuckDB path {db_path} does not exist.")
        return []

    try:
        with duckdb.connect(db_path, read_only=True) as con:
            # count raw.reports per site_code
            query = """
                SELECT r.site_code, s.site_name, COUNT(r.report_id) as report_count
                FROM reports r
                LEFT JOIN sites s ON r.site_code = s.site_code
                GROUP BY r.site_code, s.site_name
            """
            
            data = con.execute(query).fetchall()
            if not data:
                return []
                
            counts = [row[2] for row in data]
            if not counts:
                return []
                
            peer_mean = sum(counts) / len(counts)
            variance = sum((x - peer_mean) ** 2 for x in counts) / (len(counts) - 1) if len(counts) > 1 else 0
            peer_std = math.sqrt(variance)
            
            results = []
            for site_code, site_name, count in data:
                z_score = (count - peer_mean) / peer_std if peer_std > 0 else 0.0
                flagged = z_score < -2.0
                
                risk_level = "HIGH" if flagged else ("MEDIUM" if z_score < -1.0 else "LOW")
                
                results.append({
                    "site_code": site_code,
                    "site_name": site_name or "Unknown",
                    "report_count": count,
                    "peer_mean": peer_mean,
                    "peer_std": peer_std,
                    "z_score": z_score,
                    "flagged": flagged,
                    "risk_level": risk_level
                })
                
            return results
    except Exception as e:
        logger.error(f"Error computing blindspots: {e}")
        return []
