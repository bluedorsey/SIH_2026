from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
import sqlalchemy as sa
from sqlalchemy.engine import Connection

from SERVER.DB.models import reports, verdicts, spans, precursor_links
try:
    from INFERENCE.pipeline import analyse as run_pipeline
except ImportError:
    run_pipeline = None

def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

def ingest_single_report(session: Connection, text: str, source: str, site_code: str, meta: dict, report_id: str) -> dict:
    if run_pipeline is None:
        raise RuntimeError("Inference pipeline not available")
        
    text_hash = _hash_text(text)
    
    # Check duplicate
    query = sa.select(reports.c.report_id).where(reports.c.raw_text_hash == text_hash)
    existing = session.execute(query).scalar()
    if existing:
        return {"report_id": existing, "status": "duplicate"}
        
    # Insert report
    ins_report = sa.insert(reports).values(
        report_id=report_id,
        source=source,
        site_code=site_code,
        raw_text=text,
        raw_text_hash=text_hash,
        metadata=meta,
        ingested_at=datetime.now(timezone.utc)
    ).returning(reports.c.report_id)
    session.execute(ins_report)
    
    # Run pipeline
    output = run_pipeline(text, str(report_id), meta, use_models=True)
    
    # Extract
    verdict_label = output['verdict']['label']
    confidence = output['verdict']['confidence']
    review_required = output['review']['required']
    
    q1 = output['eei_facts']['high_energy_present']['value']
    q2 = output['eei_facts']['energy_released']['value']
    q3 = output['eei_facts']['serious_injury']['value']
    q4 = output['eei_facts']['direct_control_present']['value']
    
    q1 = None if q1 == 'unknown' else q1
    q2 = None if q2 == 'unknown' else q2
    q3 = None if q3 == 'unknown' else q3
    q4 = None if q4 == 'unknown' else q4
    
    lsrs = output['safety_knowledge']['lsr']
    lsr_primary = lsrs[0] if lsrs else None
    lsr_secondary = lsrs[1:] if lsrs and len(lsrs) > 1 else None
    
    activity = output['meta'].get('activity') or output['safety_knowledge'].get('activity')
    
    # Insert verdict
    ins_verdict = sa.insert(verdicts).values(
        report_id=report_id,
        verdict=verdict_label,
        confidence=confidence,
        review_required=review_required,
        is_current=True,
        produced_at=datetime.now(timezone.utc),
        pipeline_version=output['provenance']['pipeline_version'],
        q1_high_energy=q1,
        q2_energy_released=q2,
        q3_person_exposed=q3,
        q4_control_effective=q4,
        lsr_primary=lsr_primary,
        lsr_secondary=lsr_secondary,
        activity=activity,
        hazard=output['safety_knowledge']['hazard'],
        barrier=output['safety_knowledge']['barrier'],
        barrier_status=output['safety_knowledge']['barrier_failure_mode'],
        potential_consequence=output['safety_knowledge']['potential_consequence'],
        explanation=output['verdict']['decision_path'],
        energy_detail=output.get('energy'),
        uc_ua_detail=output.get('uc_ua'),
        full_output=output
    ).returning(verdicts.c.verdict_id)
    verdict_id = session.execute(ins_verdict).scalar()
    
    # Insert spans
    span_rows = []
    for s in output.get('spans', []):
        span_rows.append({
            'verdict_id': verdict_id,
            'role': s['role'],
            'text_span': s['text'],
            'char_start': s['start'],
            'char_end': s['end'],
            'source': s['source'],
            'score': s.get('score')
        })
    if span_rows:
        session.execute(sa.insert(spans), span_rows)
        
    # Precursors
    precursor_cluster = output['safety_knowledge'].get('precursor_cluster')
    if precursor_cluster:
        session.execute(sa.insert(precursor_links).values(
            verdict_id=verdict_id,
            precursor_code=precursor_cluster
        ))
        
    return {
        "report_id": report_id,
        "verdict_id": verdict_id,
        "verdict": verdict_label,
        "confidence": confidence
    }

def ingest_csv_batch(session: Connection, rows: list[dict]) -> dict:
    import uuid
    job_id = str(uuid.uuid4())
    processed = 0
    failed = 0
    errors = []
    
    for row in rows:
        try:
            # Assuming row has text, source, site_code, meta, report_id
            text = row.get("text", "")
            source = row.get("source", "csv")
            site_code = row.get("site_code", "UNKNOWN")
            meta = row.get("meta", {})
            report_id = row.get("report_id", str(uuid.uuid4()))
            
            ingest_single_report(session, text, source, site_code, meta, report_id)
            processed += 1
        except Exception as e:
            failed += 1
            errors.append(str(e))
            
    return {
        "job_id": job_id,
        "total_rows": len(rows),
        "rows_processed": processed,
        "rows_failed": failed,
        "errors": errors
    }
