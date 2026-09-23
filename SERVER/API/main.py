from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from SERVER.API.config import get_settings
from SERVER.API.routers import ingest, queue, reports, patterns, sites, review, system, compat

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info('OILENS API starting')
    try:
        from INFERENCE.pipeline import warm_models
        # warm_models() # optional
    except Exception as e:
        logger.warning(f"Could not warm models: {e}")
    yield
    logger.info('OILENS API shutting down')

app = FastAPI(title='OILENS API', version='0.7.0', lifespan=lifespan)

settings = get_settings()
if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(ingest.router, prefix="/api/ingest")
app.include_router(queue.router, prefix="/api/queue")
app.include_router(reports.router, prefix="/api/reports")
app.include_router(patterns.router, prefix="/api/patterns")
app.include_router(sites.router, prefix="/api/sites")
app.include_router(review.router, prefix="/api/review")
app.include_router(system.router, prefix="/api/system")
app.include_router(compat.router)

@app.get("/")
def root():
    return {"name": "OILENS API", "version": "0.7.0", "docs": "/docs"}
