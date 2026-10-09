"""Loads and validates environment configuration."""
from __future__ import annotations
import os
from dataclasses import dataclass

@dataclass
class Config:
    api_token: str
    database_url: str
    log_level: str

def load_config() -> Config:
    api_token = os.environ.get("RELAYBOX_API_TOKEN")
    if not api_token:
        raise RuntimeError("RELAYBOX_API_TOKEN is missing")
    return Config(
        api_token=api_token,
        database_url=os.environ.get("RELAYBOX_DATABASE_URL", "postgresql://relaybox:relaybox@db:5432/relaybox"),
        log_level=os.environ.get("RELAYBOX_LOG_LEVEL", "info"),
    )
