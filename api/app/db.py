"""Database connection pool and migration execution."""
from __future__ import annotations
import asyncpg
from pathlib import Path

async def create_pool(dsn: str) -> asyncpg.Pool:
    pool = await asyncpg.create_pool(dsn)
    if pool is None:
        raise RuntimeError("Failed to create database pool")
    return pool

async def run_migrations(pool: asyncpg.Pool):
    migrations_dir = Path(__file__).resolve().parent.parent.parent / 'db' / 'migrations'
    if not migrations_dir.exists():
        return
    
    async with pool.acquire() as conn:
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS _migrations (
                filename TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ DEFAULT NOW()
            )
        ''')
        
        sql_files = sorted(migrations_dir.glob('*.sql'))
        for sql_file in sql_files:
            filename = sql_file.name
            applied = await conn.fetchval('SELECT filename FROM _migrations WHERE filename = $1', filename)
            if not applied:
                content = sql_file.read_text()
                async with conn.transaction():
                    await conn.execute(content)
                    await conn.execute('INSERT INTO _migrations (filename) VALUES ($1)', filename)
