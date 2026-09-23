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

def compute_cusum(precursor_code: str, site_code: str, period: str = 'month', duckdb_path: str | None = None) -> list[dict]:
    """Computes CUSUM for a precursor and site."""
    db_path = _get_duckdb_path(duckdb_path)
    if not os.path.exists(db_path):
        logger.warning(f"DuckDB path {db_path} does not exist.")
        return []

    try:
        with duckdb.connect(db_path, read_only=True) as con:
            time_format = '%Y-%m' if period == 'month' else '%Y-%W'
            
            query = f"""
                SELECT strftime(r.ingested_at, '{time_format}') as period, COUNT(*) as cnt
                FROM verdicts v
                JOIN reports r ON v.report_id = r.report_id
                WHERE v.precursor_code = ? AND r.site_code = ?
                  AND v.verdict IN ('H_SIF', 'L_SIF', 'P_SIF', 'EXPOSURE')
                GROUP BY period
                ORDER BY period
            """
            data = con.execute(query, [precursor_code, site_code]).fetchall()
            
            if not data:
                return []
                
            counts = [row[1] for row in data]
            periods = [row[0] for row in data]
            
            if len(counts) < 2:
                return [{"period": periods[0], "count": counts[0], "cusum": 0.0, "baseline_mean": counts[0], "flagged": False}]
                
            baseline_mean = sum(counts) / len(counts)
            variance = sum((x - baseline_mean) ** 2 for x in counts) / (len(counts) - 1) if len(counts) > 1 else 0
            std_dev = math.sqrt(variance)
            
            k = 0.5 * std_dev
            h = max(4 * std_dev, 5) # 4*std or 5 if std is small
            
            cusum = 0.0
            results = []
            
            for p, c in zip(periods, counts):
                cusum = max(0, cusum + c - baseline_mean - k)
                flagged = cusum > h
                results.append({
                    "period": p,
                    "count": c,
                    "cusum": cusum,
                    "baseline_mean": baseline_mean,
                    "flagged": flagged
                })
            
            return results
    except Exception as e:
        logger.error(f"Error computing CUSUM: {e}")
        return []
