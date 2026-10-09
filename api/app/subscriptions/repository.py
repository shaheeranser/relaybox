"""CRUD persistence for subscriptions."""
from __future__ import annotations
import asyncpg

async def create(pool: asyncpg.Pool, id: str, url: str, secret: str, event_types: list[str], active: bool, description: str | None) -> asyncpg.Record:
    async with pool.acquire() as conn:
        return await conn.fetchrow('''
            INSERT INTO subscriptions (id, url, secret, event_types, active, description, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, NOW(), NOW())
            RETURNING *
        ''', id, url, secret, event_types, active, description)

async def get(pool: asyncpg.Pool, id: str) -> asyncpg.Record | None:
    async with pool.acquire() as conn:
        return await conn.fetchrow('SELECT * FROM subscriptions WHERE id = $1', id)

async def list_all(pool: asyncpg.Pool) -> list[asyncpg.Record]:
    async with pool.acquire() as conn:
        return await conn.fetch('SELECT * FROM subscriptions ORDER BY created_at DESC')

async def update(pool: asyncpg.Pool, id: str, **fields) -> asyncpg.Record | None:
    if not fields:
        return await get(pool, id)
    
    set_clauses = []
    values = []
    for i, (k, v) in enumerate(fields.items(), start=1):
        set_clauses.append(f"{k} = ${i}")
        values.append(v)
    
    values.append(id)
    set_clauses.append("updated_at = NOW()")
    
    query = f'''
        UPDATE subscriptions 
        SET {", ".join(set_clauses)}
        WHERE id = ${len(values)}
        RETURNING *
    '''
    async with pool.acquire() as conn:
        return await conn.fetchrow(query, *values)

async def delete(pool: asyncpg.Pool, id: str) -> bool:
    async with pool.acquire() as conn:
        res = await conn.execute('DELETE FROM subscriptions WHERE id = $1', id)
        return res.endswith('1')

async def get_matching(pool: asyncpg.Pool, event_type: str) -> list[asyncpg.Record]:
    async with pool.acquire() as conn:
        return await conn.fetch('''
            SELECT * FROM subscriptions 
            WHERE active = true 
            AND ($1 = ANY(event_types) OR '*' = ANY(event_types))
        ''', event_type)
