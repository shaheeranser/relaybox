"""Worker entrypoint with graceful shutdown."""
from __future__ import annotations

import asyncio
import logging
import signal
import sys
import json

import asyncpg
import httpx

from app.config import load_config
from app.loop import run_loop


async def main() -> None:
    config = load_config()

    logging.basicConfig(
        level=config.log_level.upper(),
        format="%(message)s",
        stream=sys.stdout,
    )
    logger = logging.getLogger(__name__)

    pool = await asyncpg.create_pool(dsn=config.database_url)
    client = httpx.AsyncClient()

    shutdown_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, shutdown_event.set)

    logger.info(json.dumps({"event": "worker_started"}))
    
    try:
        await run_loop(pool, client, config, shutdown_event)
    finally:
        await client.aclose()
        await pool.close()
        logger.info(json.dumps({"event": "worker_stopped"}))


if __name__ == '__main__':
    asyncio.run(main())
