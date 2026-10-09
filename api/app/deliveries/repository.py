"""Query and update deliveries and attempts."""
from __future__ import annotations
import asyncpg

async def list_deliveries(pool: asyncpg.Pool, status: str | None, subscription_id: str | None, event_id: str | None, cursor: dict | None, limit: int):
    conditions, values = [], []
    if status:
        values.append(status)
        conditions.append(f"status = ${len(values)}")
    if subscription_id:
        values.append(subscription_id)
        conditions.append(f"subscription_id = ${len(values)}")
    if event_id:
        values.append(event_id)
        conditions.append(f"event_id = ${len(values)}")
    
    if cursor:
        values.extend([cursor['t'], cursor['id']])
        conditions.append(f"(created_at, id) < (${len(values)-1}, ${len(values)})")
        
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    values.append(limit + 1)
    
    query = f"SELECT * FROM deliveries {where} ORDER BY created_at DESC, id DESC LIMIT ${len(values)}"
    async with pool.acquire() as conn:
        records = await conn.fetch(query, *values)
        
    has_more = len(records) > limit
    return records[:limit], has_more

async def get_delivery(pool: asyncpg.Pool, id: str) -> asyncpg.Record | None:
    async with pool.acquire() as conn:
        return await conn.fetchrow('SELECT * FROM deliveries WHERE id = $1', id)

async def get_delivery_with_attempts(pool: asyncpg.Pool, id: str) -> tuple[asyncpg.Record, list[asyncpg.Record]] | None:
    delivery = await get_delivery(pool, id)
    if not delivery: return None
    async with pool.acquire() as conn:
        attempts = await conn.fetch('SELECT * FROM delivery_attempts WHERE delivery_id = $1 ORDER BY attempt_no ASC', id)
    return delivery, attempts

async def list_dead_letter(pool: asyncpg.Pool, cursor: dict | None, limit: int):
    return await list_deliveries(pool, 'dead', None, None, cursor, limit)

async def replay_delivery(pool: asyncpg.Pool, id: str) -> asyncpg.Record | None:
    async with pool.acquire() as conn:
        return await conn.fetchrow('''
            UPDATE deliveries
            SET status = 'pending', attempts = 0, next_attempt_at = NOW(), 
                locked_until = NULL, last_error = NULL, updated_at = NOW()
            WHERE id = $1
            RETURNING *
        ''', id)
