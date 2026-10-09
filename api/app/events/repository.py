"""Persist events and create fan-out deliveries."""
from __future__ import annotations
import uuid
import json
import asyncpg

async def create_event(pool: asyncpg.Pool, id: str, type: str, payload: dict, idempotency_key: str | None) -> asyncpg.Record:
    async with pool.acquire() as conn:
        return await conn.fetchrow('''
            INSERT INTO events (id, type, payload, idempotency_key, received_at)
            VALUES ($1, $2, $3, $4, NOW())
            RETURNING *
        ''', id, type, json.dumps(payload), idempotency_key)

async def get_event(pool: asyncpg.Pool, id: str) -> asyncpg.Record | None:
    async with pool.acquire() as conn:
        return await conn.fetchrow('SELECT * FROM events WHERE id = $1', id)

async def check_idempotency(pool: asyncpg.Pool, key: str) -> asyncpg.Record | None:
    async with pool.acquire() as conn:
        return await conn.fetchrow('SELECT * FROM events WHERE idempotency_key = $1', key)

async def fan_out(pool: asyncpg.Pool, event_id: str, subscriptions: list) -> int:
    if not subscriptions: return 0
    
    values = []
    placeholders = []
    for i, sub in enumerate(subscriptions):
        del_id = str(uuid.uuid4())
        values.extend([del_id, event_id, sub['id']])
        idx = i * 3
        placeholders.append(f"(${idx+1}, ${idx+2}, ${idx+3}, 'pending', NOW(), NOW())")
    
    query = f'''
        INSERT INTO deliveries (id, event_id, subscription_id, status, created_at, updated_at)
        VALUES {", ".join(placeholders)}
    '''
    async with pool.acquire() as conn:
        await conn.execute(query, *values)
    return len(subscriptions)
