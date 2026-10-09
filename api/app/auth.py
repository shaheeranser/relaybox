"""Bearer token authentication for /v1 routes."""
from __future__ import annotations
import hmac
from fastapi import Header, HTTPException
from app.config import Config

config: Config | None = None

def verify_token(authorization: str = Header(...)):
    if config is None:
        raise HTTPException(status_code=500, detail="Auth not configured")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token prefix")
    token = authorization[7:]
    if not hmac.compare_digest(token, config.api_token):
        raise HTTPException(status_code=401, detail="Invalid API token")
