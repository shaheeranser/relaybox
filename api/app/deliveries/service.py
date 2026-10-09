"""Delivery listing, detail, replay, and dead-letter queries."""
from __future__ import annotations
import base64
import json
import asyncpg
from app.models import DeliveryOut, DeliveryDetail, AttemptOut, PaginatedDeliveries
from app.deliveries import repository

def encode_cursor(t: str, id: str) -> str:
    return base64.urlsafe_b64encode(json.dumps({"t": t, "id": id}).encode()).decode()

def decode_cursor(c: str | None) -> dict | None:
    if not c: return None
    try:
        return json.loads(base64.urlsafe_b64decode(c.encode()).decode())
    except Exception:
        return None

async def list_deliveries(pool: asyncpg.Pool, status: str | None, subscription_id: str | None, event_id: str | None, cursor: str | None, limit: int) -> PaginatedDeliveries:
    c_dict = decode_cursor(cursor)
    records, has_more = await repository.list_deliveries(pool, status, subscription_id, event_id, c_dict, limit)
    items = [DeliveryOut(**dict(r)) for r in records]
    next_c = encode_cursor(items[-1].created_at.isoformat(), items[-1].id) if has_more and items else None
    return PaginatedDeliveries(items=items, next_cursor=next_c)

async def get_delivery_detail(pool: asyncpg.Pool, id: str) -> DeliveryDetail | None:
    res = await repository.get_delivery_with_attempts(pool, id)
    if not res: return None
    delivery, attempts = res
    d_dict = dict(delivery)
    d_dict['attempt_history'] = [AttemptOut(**dict(a)) for a in attempts]
    return DeliveryDetail(**d_dict)

async def list_dead_letter(pool: asyncpg.Pool, cursor: str | None, limit: int) -> PaginatedDeliveries:
    c_dict = decode_cursor(cursor)
    records, has_more = await repository.list_dead_letter(pool, c_dict, limit)
    items = [DeliveryOut(**dict(r)) for r in records]
    next_c = encode_cursor(items[-1].created_at.isoformat(), items[-1].id) if has_more and items else None
    return PaginatedDeliveries(items=items, next_cursor=next_c)

async def replay_delivery(pool: asyncpg.Pool, id: str) -> DeliveryOut | None:
    record = await repository.replay_delivery(pool, id)
    if not record: return None
    return DeliveryOut(**dict(record))
