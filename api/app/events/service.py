"""Idempotency check and fan-out orchestration."""
from __future__ import annotations
import uuid
import json
import asyncpg
from app.models import CreateEvent, EventCreated, EventDetail, DeliveryBrief
from app.events import repository
from app.subscriptions.repository import get_matching

async def accept_event(pool: asyncpg.Pool, data: CreateEvent) -> EventCreated:
    if data.idempotency_key:
        existing = await repository.check_idempotency(pool, data.idempotency_key)
        if existing:
            async with pool.acquire() as conn:
                count = await conn.fetchval('SELECT count(*) FROM deliveries WHERE event_id = $1', existing['id'])
            return EventCreated(event_id=str(existing['id']), deliveries_created=count)
    
    event_id = str(uuid.uuid4())
    await repository.create_event(pool, event_id, data.type, data.payload, data.idempotency_key)
    subs = await get_matching(pool, data.type)
    count = await repository.fan_out(pool, event_id, subs)
    return EventCreated(event_id=event_id, deliveries_created=count)

async def get_event_detail(pool: asyncpg.Pool, event_id: str) -> EventDetail | None:
    event_rec = await repository.get_event(pool, event_id)
    if not event_rec: return None
    
    async with pool.acquire() as conn:
        del_recs = await conn.fetch('SELECT id, subscription_id, status, attempts, created_at FROM deliveries WHERE event_id = $1 ORDER BY created_at DESC', event_id)
    
    payload = event_rec['payload']
    if isinstance(payload, str): payload = json.loads(payload)
    deliveries = [DeliveryBrief(**dict(d)) for d in del_recs]
    return EventDetail(
        id=event_rec['id'], type=event_rec['type'], payload=payload,
        idempotency_key=event_rec['idempotency_key'], received_at=event_rec['received_at'],
        deliveries=deliveries
    )
