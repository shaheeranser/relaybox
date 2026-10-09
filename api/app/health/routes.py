"""Health check and Prometheus metrics endpoints."""
from __future__ import annotations
import time
from fastapi import APIRouter, Request, Response
from app.models import HealthResponse

router = APIRouter(tags=["health"])
start_time = time.time()

@router.get("/health", response_model=HealthResponse)
async def health(request: Request):
    uptime_s = time.time() - start_time
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        queue_depth = await conn.fetchval("SELECT count(*) FROM deliveries WHERE status IN ('pending', 'failed')")
    return HealthResponse(status="ok", version="0.1.0", uptime_s=uptime_s, queue_depth=queue_depth)

@router.get("/metrics")
async def metrics(request: Request):
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        events_total = await conn.fetchval("SELECT count(*) FROM events")
        delivery_stats = await conn.fetch("SELECT status, count(*) as c FROM deliveries GROUP BY status")
        
    lines = [
        "# HELP relaybox_events_accepted_total Total number of accepted events",
        "# TYPE relaybox_events_accepted_total counter",
        f"relaybox_events_accepted_total {events_total}",
        "# HELP relaybox_deliveries_total Total deliveries by status",
        "# TYPE relaybox_deliveries_total counter"
    ]
    
    queue_depth = 0
    for stat in delivery_stats:
        status, count = stat['status'], stat['c']
        lines.append(f'relaybox_deliveries_total{{status="{status}"}} {count}')
        if status in ('pending', 'failed'): queue_depth += count
            
    lines.extend([
        "# HELP relaybox_queue_depth Deliveries pending or failed",
        "# TYPE relaybox_queue_depth gauge",
        f"relaybox_queue_depth {queue_depth}"
    ])
    return Response(content="\n".join(lines) + "\n", media_type="text/plain")
