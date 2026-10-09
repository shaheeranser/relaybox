"""Execute a single delivery attempt."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
import asyncpg
import httpx

from app.config import Config
from app.signing import build_headers
from app.retry import next_attempt_at

logger = logging.getLogger(__name__)


async def execute_delivery(pool: asyncpg.Pool, client: httpx.AsyncClient, delivery: asyncpg.Record, config: Config) -> None:
    delivery_id = str(delivery['id'])
    event_id = delivery['event_id']
    subscription_id = delivery['subscription_id']
    attempt_no = delivery['attempts'] + 1

    async with pool.acquire() as conn:
        record = await conn.fetchrow(
            """
            SELECT s.url, s.secret, e.type, e.payload
            FROM subscriptions s JOIN events e ON e.id = $1
            WHERE s.id = $2
            """,
            event_id, subscription_id
        )

    if not record:
        logger.error(json.dumps({"event": "delivery_failed", "delivery_id": delivery_id, "error": "Subscription or Event not found"}))
        return

    url = record['url']
    secret = record['secret']
    event_type = record['type']
    payload = record['payload']

    payload_bytes = payload.encode('utf-8') if isinstance(payload, str) else json.dumps(payload).encode('utf-8')
    headers = build_headers(secret, payload_bytes, event_type, delivery_id, attempt_no)
    
    started_at = datetime.now(timezone.utc)
    
    try:
        response = await client.post(url, content=payload_bytes, headers=headers, timeout=config.http_timeout)
        finished_at = datetime.now(timezone.utc)
        duration_ms = int((finished_at - started_at).total_seconds() * 1000)
        
        status_code = response.status_code
        
        async with pool.acquire() as conn:
            if 200 <= status_code < 300:
                await conn.execute(
                    """
                    INSERT INTO delivery_attempts (delivery_id, attempt_no, status_code, duration_ms, started_at, finished_at)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                    delivery['id'], attempt_no, status_code, duration_ms, started_at, finished_at
                )
                await conn.execute(
                    """
                    UPDATE deliveries
                    SET status = 'succeeded', attempts = $1, locked_until = NULL, updated_at = now()
                    WHERE id = $2
                    """,
                    attempt_no, delivery['id']
                )
                logger.info(json.dumps({"event": "delivery_succeeded", "delivery_id": delivery_id, "attempt": attempt_no, "status_code": status_code}))
            else:
                retry_after = response.headers.get("Retry-After")
                retry_after_int = None
                if retry_after:
                    try:
                        retry_after_int = int(retry_after)
                    except ValueError:
                        pass
                
                await conn.execute(
                    """
                    INSERT INTO delivery_attempts (delivery_id, attempt_no, status_code, error, duration_ms, started_at, finished_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """,
                    delivery['id'], attempt_no, status_code, f"HTTP {status_code}", duration_ms, started_at, finished_at
                )
                
                if attempt_no >= config.max_attempts:
                    await conn.execute(
                        "UPDATE deliveries SET status = 'dead', attempts = $1, locked_until = NULL, last_error = $2, updated_at = now() WHERE id = $3",
                        attempt_no, f"HTTP {status_code}", delivery['id']
                    )
                else:
                    next_attempt = next_attempt_at(attempt_no, retry_after_int)
                    await conn.execute(
                        "UPDATE deliveries SET status = 'failed', attempts = $1, next_attempt_at = $2, locked_until = NULL, last_error = $3, updated_at = now() WHERE id = $4",
                        attempt_no, next_attempt, f"HTTP {status_code}", delivery['id']
                    )
                logger.warning(json.dumps({"event": "delivery_failed", "delivery_id": delivery_id, "attempt": attempt_no, "status_code": status_code}))

    except Exception as exc:
        finished_at = datetime.now(timezone.utc)
        duration_ms = int((finished_at - started_at).total_seconds() * 1000)
        error_msg = str(exc)
        
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO delivery_attempts (delivery_id, attempt_no, error, duration_ms, started_at, finished_at)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                delivery['id'], attempt_no, error_msg, duration_ms, started_at, finished_at
            )
            
            if attempt_no >= config.max_attempts:
                await conn.execute(
                    "UPDATE deliveries SET status = 'dead', attempts = $1, locked_until = NULL, last_error = $2, updated_at = now() WHERE id = $3",
                    attempt_no, error_msg, delivery['id']
                )
            else:
                next_attempt = next_attempt_at(attempt_no)
                await conn.execute(
                    "UPDATE deliveries SET status = 'failed', attempts = $1, next_attempt_at = $2, locked_until = NULL, last_error = $3, updated_at = now() WHERE id = $4",
                    attempt_no, next_attempt, error_msg, delivery['id']
                )
        logger.error(json.dumps({"event": "delivery_error", "delivery_id": delivery_id, "attempt": attempt_no, "error": error_msg}))
