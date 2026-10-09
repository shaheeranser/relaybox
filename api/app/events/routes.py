"""HTTP endpoints for /v1/events."""
from __future__ import annotations
from fastapi import APIRouter, Depends, Request, HTTPException
from app.auth import verify_token
from app.models import CreateEvent, EventCreated, EventDetail
from app.events import service

router = APIRouter(prefix="/v1/events", tags=["events"], dependencies=[Depends(verify_token)])

@router.post("", response_model=EventCreated, status_code=202)
async def create(request: Request, data: CreateEvent):
    return await service.accept_event(request.app.state.pool, data)

@router.get("/{id}", response_model=EventDetail)
async def get(request: Request, id: str):
    event = await service.get_event_detail(request.app.state.pool, id)
    if not event:
        raise HTTPException(status_code=404, detail="Not found")
    return event
