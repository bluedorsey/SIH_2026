from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Any
import hashlib
import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy.orm import Session

from SERVER.API.deps import db_session
from SERVER.DB.models import reports, verdicts, spans as spans_table, precursor_links

try:
    from INFERENCE.pipeline import analyse as run_pipeline
except ImportError:
    run_pipeline = None

router = APIRouter(tags=["compat"])

class AnalyseRequest(BaseModel):
    text: str
    report_id: str | None = None
    meta: dict[str, Any] | None = None

class BatchItem(BaseModel):
    text: str
    report_id: str | None = None
    meta: dict[str, Any] | None = None


def _persist_result(session: Session, text: str, report_id: str, meta: dict | None, result: dict):
    """Save the analysis result to raw.reports + derived.verdicts + derived.spans.
    
    NOTE: Do NOT commit here — the FastAPI db_session dependency auto-commits
    at the end of the request.
    """
    try:
        text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()

        # Check duplicate
        existing = session.execute(
            sa.select(reports.c.report_id).where(reports.c.raw_text_hash == text_hash)
        ).scalar()
        if existing:
            return  # already persisted

        site_code = (meta or {}).get("site") or None

        # Insert raw report
        session.execute(sa.insert(reports).values(
            report_id=report_id,
            source="frontend",
            site_code=site_code,
            raw_text=text,
            raw_text_hash=text_hash,
            metadata=meta,
            ingested_at=datetime.now(timezone.utc),
        ))

        # Extract verdict info from the flattened result
        v = result.get("verdict_detail") or result.get("verdict", {})
        if isinstance(v, str):
            verdict_label = v
            confidence = None
            decision_path = None
        else:
            verdict_label = v.get("label", result.get("verdict", "UNKNOWN"))
            confidence = v.get("confidence")
            decision_path = v.get("decision_path")

        eei = result.get("eei_facts", {}) or {}

        def _bool(val):
            if val is None or val == "unknown":
                return None
            if isinstance(val, dict):
                v2 = val.get("value")
                return None if v2 == "unknown" else v2
            return val

        sk = result.get("safety_knowledge", {}) or {}
        lsrs = sk.get("lsr") or []
        review = result.get("review", {}) or {}
        prov = result.get("provenance", {}) or {}
        energy = result.get("energy")
        uc_ua = result.get("uc_ua")

        ins_verdict = sa.insert(verdicts).values(
            report_id=report_id,
            verdict=verdict_label,
            confidence=confidence,
            review_required=review.get("required", False),
            is_current=True,
            produced_at=datetime.now(timezone.utc),
            pipeline_version=prov.get("pipeline_version", "0.7.0"),
            q1_high_energy=_bool(eei.get("high_energy_present")),
            q2_energy_released=_bool(eei.get("energy_released")),
            q3_person_exposed=_bool(eei.get("serious_injury")),
            q4_control_effective=_bool(eei.get("direct_control_present")),
            lsr_primary=lsrs[0] if lsrs else None,
            lsr_secondary=lsrs[1:] if len(lsrs) > 1 else None,
            activity=(meta or {}).get("activity") or sk.get("activity"),
            hazard=sk.get("hazard"),
            barrier=sk.get("barrier"),
            barrier_status=sk.get("barrier_failure_mode"),
            potential_consequence=sk.get("potential_consequence"),
            explanation=decision_path,
            energy_detail=energy,
            uc_ua_detail=uc_ua,
            full_output=result,
        ).returning(verdicts.c.verdict_id)
        verdict_id = session.execute(ins_verdict).scalar()

        # Insert spans
        span_rows = []
        for s in result.get("spans", []) or []:
            span_rows.append({
                "verdict_id": verdict_id,
                "role": s.get("role", "unknown"),
                "text_span": s.get("text", ""),
                "char_start": s.get("start"),
                "char_end": s.get("end"),
                "source": s.get("source", "pipeline"),
                "score": s.get("score"),
            })
        if span_rows:
            session.execute(sa.insert(spans_table), span_rows)

        # Precursor links
        precursor_cluster = sk.get("precursor_cluster")
        if precursor_cluster:
            try:
                session.execute(sa.insert(precursor_links).values(
                    verdict_id=verdict_id,
                    precursor_code=precursor_cluster,
                ))
            except Exception:
                pass  # FK violation if precursor not in reference table

        # Flush to DB within current transaction — commit handled by dependency
        session.commit()

    except Exception as e:
        import traceback
        with open("e:\\SIH_26\\persist_error2.txt", "w") as f:
            f.write(traceback.format_exc())
        traceback.print_exc()
        try:
            session.rollback()
        except:
            pass


@router.get("/health")
def get_health():
    layers = {"rules": True, "gliner": False, "heads": False}
    pipeline_ver = "0.7.0"
    gliner_src = "none"
    heads_list = []
    try:
        from INFERENCE.config import REPO_ROOT
        models_dir = REPO_ROOT / "SERVER" / "Classfication" / "Models"
        tuned = models_dir / "Tunned"
        raw = models_dir / "RAW"
        if (tuned / "gliner_sif").is_dir():
            layers["gliner"] = True
            gliner_src = "gliner_sif"
        elif (raw / "gliner_multi").is_dir():
            layers["gliner"] = True
            gliner_src = "gliner_multi"
        heads_dir = tuned / "sif_heads"
        if heads_dir.is_dir():
            heads_list = [f.stem for f in heads_dir.glob("*.joblib")]
            layers["heads"] = len(heads_list) > 0
    except Exception:
        pass
    return {
        "status": "ok",
        "pipeline_version": pipeline_ver,
        "package_version": pipeline_ver,
        "layers": layers,
        "gliner_source": gliner_src,
        "heads": heads_list,
    }


@router.post("/analyse")
def analyse(req: AnalyseRequest, db: Session = Depends(db_session)):
    if run_pipeline is None:
        raise HTTPException(status_code=503, detail="Models not available")

    # DB expects a valid UUID for report_id
    try:
        if req.report_id:
            uuid.UUID(req.report_id) # validate
            rid = req.report_id
        else:
            rid = str(uuid.uuid4())
    except ValueError:
        rid = str(uuid.uuid4())

    result = run_pipeline(req.text, report_id=rid, meta=req.meta, use_models=True)

    if isinstance(result, dict):
        sk = result.get("safety_knowledge", {}) or {}
        v = result.get("verdict", {}) or {}
        result.setdefault("hazard", sk.get("hazard"))
        result.setdefault("failed_control", sk.get("barrier"))
        result.setdefault("potential_consequence", sk.get("potential_consequence"))
        result.setdefault("safety_knowledge", sk)
        result.setdefault("exposure", sk.get("barrier_failure_mode"))
        if isinstance(v, dict):
            result["verdict_detail"] = v
            result["verdict"] = v.get("label", result.get("verdict"))

        # ── Persist to database ──
        _persist_result(db, req.text, rid, req.meta, result)

    return result


@router.post("/batch")
def batch_analyse(items: list[BatchItem], db: Session = Depends(db_session)):
    if run_pipeline is None:
        raise HTTPException(status_code=503, detail="Models not available")
    evaluations = []
    for item in items:
        try:
            if item.report_id:
                uuid.UUID(item.report_id)
                rid = item.report_id
            else:
                rid = str(uuid.uuid4())
        except ValueError:
            rid = str(uuid.uuid4())

        out = run_pipeline(item.text, report_id=rid, meta=item.meta, use_models=True)
        if isinstance(out, dict):
            sk = out.get("safety_knowledge", {}) or {}
            v = out.get("verdict", {}) or {}
            out.setdefault("hazard", sk.get("hazard"))
            if isinstance(v, dict):
                out["verdict_detail"] = v
                out["verdict"] = v.get("label", out.get("verdict"))
            _persist_result(db, item.text, rid, item.meta, out)
        evaluations.append(out)
    return {"total": len(evaluations), "evaluations": evaluations}
