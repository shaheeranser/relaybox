"""Worker-specific environment configuration."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class Config:
    database_url: str
    concurrency: int
    max_attempts: int
    lease_seconds: int
    http_timeout: int
    log_level: str


def load_config() -> Config:
    return Config(
        database_url=os.environ.get("RELAYBOX_DATABASE_URL", "postgresql://relaybox:relaybox@db:5432/relaybox"),
        concurrency=int(os.environ.get("RELAYBOX_WORKER_CONCURRENCY", "8")),
        max_attempts=int(os.environ.get("RELAYBOX_MAX_ATTEMPTS", "8")),
        lease_seconds=int(os.environ.get("RELAYBOX_LEASE_SECONDS", "60")),
        http_timeout=int(os.environ.get("RELAYBOX_HTTP_TIMEOUT", "10")),
        log_level=os.environ.get("RELAYBOX_LOG_LEVEL", "info"),
    )
