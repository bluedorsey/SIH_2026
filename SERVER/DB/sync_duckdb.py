from __future__ import annotations

import os
import logging
import duckdb

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def sync_duckdb() -> None:
    duckdb_path = os.getenv("DUCKDB_PATH", "SERVER/ANALYTICS/oilens_analytics.duckdb")
    postgres_dsn = os.getenv("POSTGRES_DSN")
    
    if not postgres_dsn:
        logger.error("POSTGRES_DSN environment variable is not set. Cannot sync.")
        return

    # Ensure directory exists
    os.makedirs(os.path.dirname(duckdb_path), exist_ok=True)

    try:
        logger.info(f"Connecting to DuckDB at {duckdb_path}")
        con = duckdb.connect(duckdb_path, read_only=False)
        
        logger.info("Installing and loading postgres extension")
        con.execute("INSTALL postgres;")
        con.execute("LOAD postgres;")
        
        logger.info("Attaching Postgres")
        con.execute(f"ATTACH '{postgres_dsn}' AS pg (TYPE POSTGRES, READ_ONLY);")
        
        logger.info("Syncing tables...")
        
        # verdicts (from derived.verdicts WHERE is_current)
        con.execute("CREATE OR REPLACE TABLE verdicts AS SELECT * FROM pg.derived.verdicts WHERE is_current = true;")
        
        # spans (from derived.spans)
        con.execute("CREATE OR REPLACE TABLE spans AS SELECT * FROM pg.derived.spans;")
        
        # sites (from reference.sites)
        con.execute("CREATE OR REPLACE TABLE sites AS SELECT * FROM pg.reference.sites;")
        
        # precursors (from reference.precursors)
        con.execute("CREATE OR REPLACE TABLE precursors AS SELECT * FROM pg.reference.precursors;")
        
        # life_saving_rules (from reference.life_saving_rules)
        con.execute("CREATE OR REPLACE TABLE life_saving_rules AS SELECT * FROM pg.reference.life_saving_rules;")
        
        # reports (from raw.reports)
        con.execute("CREATE OR REPLACE TABLE reports AS SELECT report_id, site_code, ingested_at, source, language_hint FROM pg.raw.reports;")
        
        # actions (from review.actions)
        con.execute("CREATE OR REPLACE TABLE actions AS SELECT * FROM pg.review.actions;")
        
        logger.info("Sync complete.")
        
    except Exception as e:
        logger.error(f"Error during DuckDB sync: {e}")
    finally:
        if 'con' in locals():
            con.close()

if __name__ == "__main__":
    sync_duckdb()
