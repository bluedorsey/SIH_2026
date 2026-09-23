from fastapi import APIRouter, Depends
from sqlalchemy.engine import Connection

from SERVER.API.deps import db_session
from SERVER.API.services import system_svc

router = APIRouter(tags=["system"])

@router.get("/health")
def get_health(db: Connection = Depends(db_session)):
    return system_svc.get_health(db)

@router.get("/models")
def get_models():
    return system_svc.get_models()

@router.get("/config")
def get_config(db: Connection = Depends(db_session)):
    return system_svc.get_config(db)

@router.get("/sync")
def get_sync_status():
    return system_svc.get_sync_status()

@router.post("/sync-analytics")
def sync_analytics():
    return {"status": "sync started"}
