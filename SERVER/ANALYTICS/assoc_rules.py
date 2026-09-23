from __future__ import annotations

import os
import logging
import duckdb
import pandas as pd
try:
    from mlxtend.frequent_patterns import apriori, association_rules
except ImportError:
    apriori = None
    association_rules = None

logger = logging.getLogger(__name__)

def _get_duckdb_path(path: str | None = None) -> str:
    if path is not None:
        return path
    return os.getenv("DUCKDB_PATH", "SERVER/ANALYTICS/oilens_analytics.duckdb")

def find_associations(min_support: float = 0.05, min_confidence: float = 0.5, duckdb_path: str | None = None) -> list[dict]:
    """Finds association rules."""
    if apriori is None:
        logger.error("mlxtend is not installed.")
        return []

    db_path = _get_duckdb_path(duckdb_path)
    if not os.path.exists(db_path):
        logger.warning(f"DuckDB path {db_path} does not exist.")
        return []

    try:
        with duckdb.connect(db_path, read_only=True) as con:
            query = """
                SELECT 
                    COALESCE(v.lsr_primary, 'UNKNOWN_LSR') as lsr_primary,
                    COALESCE(v.activity, 'UNKNOWN_ACT') as activity,
                    COALESCE(r.site_code, 'UNKNOWN_SITE') as site_code,
                    COALESCE(v.barrier_status, 'UNKNOWN_STATUS') as barrier_status
                FROM verdicts v
                JOIN reports r ON v.report_id = r.report_id
                WHERE v.verdict IN ('H_SIF', 'L_SIF', 'P_SIF', 'EXPOSURE')
            """
            
            df = con.execute(query).df()
            if df.empty or len(df) < 10:
                logger.warning("Not enough data for association rules.")
                return []
                
            # one-hot encode
            transactions = df.apply(lambda row: [
                f"LSR_{row['lsr_primary']}",
                f"ACT_{row['activity']}",
                f"SITE_{row['site_code']}",
                f"STATUS_{row['barrier_status']}"
            ], axis=1).tolist()
            
            from mlxtend.preprocessing import TransactionEncoder
            te = TransactionEncoder()
            te_ary = te.fit(transactions).transform(transactions)
            df_encoded = pd.DataFrame(te_ary, columns=te.columns_)
            
            frequent_itemsets = apriori(df_encoded, min_support=min_support, use_colnames=True)
            if frequent_itemsets.empty:
                return []
                
            rules = association_rules(frequent_itemsets, metric="confidence", min_threshold=min_confidence)
            
            results = []
            for _, row in rules.iterrows():
                results.append({
                    "antecedents": list(row["antecedents"]),
                    "consequents": list(row["consequents"]),
                    "support": float(row["support"]),
                    "confidence": float(row["confidence"]),
                    "lift": float(row["lift"])
                })
            return results
            
    except Exception as e:
        logger.error(f"Error computing association rules: {e}")
        return []
