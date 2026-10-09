"""FastAPI app construction and wiring."""
from __future__ import annotations
import logging
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.config import load_config
from app.db import create_pool, run_migrations
from app import auth
from app.subscriptions.routes import router as subs_router
from app.events.routes import router as events_router
from app.deliveries.routes import router as deliveries_router
from app.health.routes import router as health_router

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_rec = {"level": record.levelname, "message": record.getMessage(), "name": record.name}
        if record.exc_info: log_rec["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(log_rec)

def setup_logging(log_level: str):
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    logging.root.addHandler(handler)
    logging.root.setLevel(log_level.upper())

@asynccontextmanager
async def lifespan(app: FastAPI):
    config = load_config()
    setup_logging(config.log_level)
    auth.config = config
    logging.info("Starting API")
    pool = await create_pool(config.database_url)
    await run_migrations(pool)
    app.state.pool = pool
    yield
    logging.info("Shutting down API")
    await pool.close()

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Relaybox", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(subs_router)
app.include_router(events_router)
app.include_router(deliveries_router)
app.include_router(health_router)
