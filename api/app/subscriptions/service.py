"""Business rules for subscription management."""
from __future__ import annotations
import uuid
import asyncpg
from app.models import CreateSubscription, UpdateSubscription, SubscriptionOut
from app.subscriptions import repository

async def create_subscription(pool: asyncpg.Pool, data: CreateSubscription) -> SubscriptionOut:
    sub_id = str(uuid.uuid4())
    record = await repository.create(pool, sub_id, data.url, data.secret, data.event_types, data.active, data.description)
    return SubscriptionOut(**dict(record))

async def get_subscription(pool: asyncpg.Pool, id: str) -> SubscriptionOut | None:
    record = await repository.get(pool, id)
    if not record: return None
    return SubscriptionOut(**dict(record))

async def list_subscriptions(pool: asyncpg.Pool) -> list[SubscriptionOut]:
    records = await repository.list_all(pool)
    return [SubscriptionOut(**dict(r)) for r in records]

async def update_subscription(pool: asyncpg.Pool, id: str, data: UpdateSubscription) -> SubscriptionOut | None:
    fields = {k: v for k, v in data.model_dump().items() if v is not None}
    record = await repository.update(pool, id, **fields)
    if not record: return None
    return SubscriptionOut(**dict(record))

async def delete_subscription(pool: asyncpg.Pool, id: str) -> bool:
    return await repository.delete(pool, id)
