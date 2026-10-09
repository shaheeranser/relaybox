"""Main work loop — claim deliveries with lease, dispatch concurrent executions."""
from __future__ import annotations

import asyncio
import logging
import json
import asyncpg
import httpx

from app.config import Config
from app.deliver import execute_delivery

logger = logging.getLogger(__name__)


async def claim_delivery(pool: asyncpg.Pool, lease_seconds: int) -> asyncpg.Record | None:
    async with pool.acquire() as conn:
        record = await conn.fetchrow(
            """
            UPDATE deliveries
            SET status = 'delivering', locked_until = now() + make_interval(secs => $1::double precision), updated_at = now()
            WHERE id = (
                SELECT id FROM deliveries
                WHERE status IN ('pending', 'failed')
                AND next_attempt_at <= now()
                AND (locked_until IS NULL OR locked_until < now())
                ORDER BY next_attempt_at
                FOR UPDATE SKIP LOCKED
                LIMIT 1
            )
            RETURNING *;
            """,
            lease_seconds
        )
        return record


async def run_loop(pool: asyncpg.Pool, client: httpx.AsyncClient, config: Config, shutdown_event: asyncio.Event) -> None:
    semaphore = asyncio.Semaphore(config.concurrency)
    tasks: set[asyncio.Task] = set()
    idle_cycles = 0

    async def _dispatch(delivery: asyncpg.Record):
        try:
            await execute_delivery(pool, client, delivery, config)
        except Exception as e:
            logger.error(json.dumps({"event": "delivery_task_error", "error": str(e)}))
        finally:
            semaphore.release()

    while not shutdown_event.is_set():
        await semaphore.acquire()
        try:
            delivery = await claim_delivery(pool, config.lease_seconds)
            if delivery:
                idle_cycles = 0
                task = asyncio.create_task(_dispatch(delivery))
                tasks.add(task)
                task.add_done_callback(tasks.discard)
            else:
                semaphore.release()
                await asyncio.sleep(1)
                idle_cycles += 1
                if idle_cycles >= 30:
                    logger.info(json.dumps({"event": "heartbeat", "message": "Worker is idle"}))
                    idle_cycles = 0
        except Exception as e:
            semaphore.release()
            logger.error(json.dumps({"event": "claim_error", "error": str(e)}))
            await asyncio.sleep(1)

    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
