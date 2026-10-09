"""Pydantic request/response schemas shared across API domains."""
from __future__ import annotations
from pydantic import BaseModel
from datetime import datetime

class CreateEvent(BaseModel):
    type: str
    payload: dict
    idempotency_key: str | None = None

class CreateSubscription(BaseModel):
    url: str
    event_types: list[str]
    secret: str
    active: bool = True
    description: str | None = None

class UpdateSubscription(BaseModel):
    url: str | None = None
    event_types: list[str] | None = None
    secret: str | None = None
    active: bool | None = None
    description: str | None = None

class EventCreated(BaseModel):
    event_id: str
    deliveries_created: int

class DeliveryBrief(BaseModel):
    id: str
    subscription_id: str
    status: str
    attempts: int
    created_at: datetime

class EventDetail(BaseModel):
    id: str
    type: str
    payload: dict
    idempotency_key: str | None
    received_at: datetime
    deliveries: list[DeliveryBrief]

class SubscriptionOut(BaseModel):
    id: str
    url: str
    event_types: list[str]
    active: bool
    description: str | None
    created_at: datetime
    updated_at: datetime

class DeliveryOut(BaseModel):
    id: str
    event_id: str
    subscription_id: str
    status: str
    attempts: int
    next_attempt_at: datetime | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime

class AttemptOut(BaseModel):
    id: str
    attempt_no: int
    status_code: int | None
    error: str | None
    duration_ms: int | None
    started_at: datetime
    finished_at: datetime | None

class DeliveryDetail(DeliveryOut):
    attempt_history: list[AttemptOut]

class PaginatedDeliveries(BaseModel):
    items: list[DeliveryOut]
    next_cursor: str | None

class HealthResponse(BaseModel):
    status: str
    version: str
    uptime_s: float
    queue_depth: int
