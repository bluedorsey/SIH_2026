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

def compute_prr(precursor_code: str, site_code: str, duckdb_path: str | None = None) -> dict:
    """Computes PRR for a specific precursor and site."""
    db_path = _get_duckdb_path(duckdb_path)
    if not os.path.exists(db_path):
        logger.warning(f"DuckDB path {db_path} does not exist.")
        return {}

    try:
        with duckdb.connect(db_path, read_only=True) as con:
            # a = reports of this precursor at this site
            # b = other precursor reports at this site
            # c = reports of this precursor at all other sites
            # d = other precursor reports at all other sites
            # using verdicts joined with reports for site_code
            
            query = """
                SELECT 
                    SUM(CASE WHEN v.precursor_code = ? AND r.site_code = ? THEN 1 ELSE 0 END) as a,
                    SUM(CASE WHEN v.precursor_code != ? AND r.site_code = ? THEN 1 ELSE 0 END) as b,
                    SUM(CASE WHEN v.precursor_code = ? AND r.site_code != ? THEN 1 ELSE 0 END) as c,
                    SUM(CASE WHEN v.precursor_code != ? AND r.site_code != ? THEN 1 ELSE 0 END) as d
                FROM verdicts v
                JOIN reports r ON v.report_id = r.report_id
                WHERE v.verdict IN ('H_SIF', 'L_SIF', 'P_SIF', 'EXPOSURE')
            """
            
            res = con.execute(query, [precursor_code, site_code, precursor_code, site_code, precursor_code, site_code, precursor_code, site_code]).fetchone()
            if not res:
                return {}
            
            a, b, c, d = res
            a = int(a or 0)
            b = int(b or 0)
            c = int(c or 0)
            d = int(d or 0)
            
            if a + b == 0 or c + d == 0 or a == 0 or c == 0:
                return {"prr": 0.0, "ci_lower": 0.0, "ci_upper": 0.0, "a": a, "b": b, "c": c, "d": d, "flagged": False}
                
            prr = (a / (a + b)) / (c / (c + d))
            se = math.sqrt(1/a - 1/(a+b) + 1/c - 1/(c+d))
            ci_lower = math.exp(math.log(prr) - 1.96 * se)
            ci_upper = math.exp(math.log(prr) + 1.96 * se)
            
            flagged = ci_lower > 1 and a >= 3
            
            return {
                "prr": prr,
                "ci_lower": ci_lower,
                "ci_upper": ci_upper,
                "a": a,
                "b": b,
                "c": c,
                "d": d,
                "flagged": flagged
            }
    except Exception as e:
        logger.error(f"Error computing PRR: {e}")
        return {}

def compute_prr_all(duckdb_path: str | None = None) -> list[dict]:
    """Computes PRR for all precursor x site combinations."""
    db_path = _get_duckdb_path(duckdb_path)
    if not os.path.exists(db_path):
        logger.warning(f"DuckDB path {db_path} does not exist.")
        return []

    try:
        with duckdb.connect(db_path, read_only=True) as con:
            # Get all combinations
            query_combinations = """
                SELECT DISTINCT v.precursor_code, r.site_code
                FROM verdicts v
                JOIN reports r ON v.report_id = r.report_id
                WHERE v.verdict IN ('H_SIF', 'L_SIF', 'P_SIF', 'EXPOSURE')
                  AND v.precursor_code IS NOT NULL
                  AND r.site_code IS NOT NULL
            """
            combinations = con.execute(query_combinations).fetchall()
            
            results = []
            for precursor_code, site_code in combinations:
                res = compute_prr(precursor_code, site_code, db_path)
                if res:
                    res["precursor_code"] = precursor_code
                    res["site_code"] = site_code
                    results.append(res)
            return results
    except Exception as e:
        logger.error(f"Error computing all PRR: {e}")
        return []
