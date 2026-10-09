"""Configurable test receiver that stands in for a customer webhook endpoint."""
from __future__ import annotations

import os
import time
import asyncio
from typing import Any
from fastapi import FastAPI, Request
from fastapi.responses import Response
import logging
import json

app = FastAPI(title="Relaybox Sink")

webhooks: list[dict[str, Any]] = []

def get_config():
    return {
        "status_code": int(os.environ.get("SINK_STATUS_CODE", "200")),
        "delay_ms": int(os.environ.get("SINK_DELAY_MS", "0")),
    }

@app.get("/")
async def get_root():
    return {
        "received": len(webhooks),
        "last": webhooks[-1] if webhooks else None
    }

@app.get("/webhooks")
async def get_webhooks():
    return list(reversed(webhooks))

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"])
async def catch_all(request: Request, path: str):
    config = get_config()
    
    body = await request.body()
    try:
        body_decoded = body.decode('utf-8')
        try:
            body_json = json.loads(body_decoded)
            body_to_store = body_json
        except json.JSONDecodeError:
            body_to_store = body_decoded
    except Exception:
        body_to_store = "<binary>"

    webhook_data = {
        "ts": time.time(),
        "method": request.method,
        "path": f"/{path}",
        "headers": dict(request.headers),
        "body": body_to_store,
    }
    
    logging.info(json.dumps(webhook_data))
    
    webhooks.append(webhook_data)
    if len(webhooks) > 1000:
        webhooks.pop(0)
        
    if config["delay_ms"] > 0:
        await asyncio.sleep(config["delay_ms"] / 1000.0)
        
    return Response(status_code=config["status_code"])
