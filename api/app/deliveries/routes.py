"""HTTP endpoints for /v1/deliveries and /v1/dead-letter."""
from __future__ import annotations
from fastapi import APIRouter, Depends, Request, HTTPException, Query
from app.auth import verify_token
from app.models import DeliveryOut, DeliveryDetail, PaginatedDeliveries
from app.deliveries import service

router = APIRouter(tags=["deliveries"], dependencies=[Depends(verify_token)])

@router.get("/v1/deliveries", response_model=PaginatedDeliveries)
async def list_deliveries(request: Request, status: str | None = None, subscription_id: str | None = None, event_id: str | None = None, cursor: str | None = None, limit: int = Query(50, ge=1, le=200)):
    return await service.list_deliveries(request.app.state.pool, status, subscription_id, event_id, cursor, limit)

@router.get("/v1/deliveries/{id}", response_model=DeliveryDetail)
async def get_delivery(request: Request, id: str):
    delivery = await service.get_delivery_detail(request.app.state.pool, id)
    if not delivery: raise HTTPException(status_code=404, detail="Not found")
    return delivery

@router.post("/v1/deliveries/{id}/replay", response_model=DeliveryOut)
async def replay(request: Request, id: str):
    delivery = await service.replay_delivery(request.app.state.pool, id)
    if not delivery: raise HTTPException(status_code=404, detail="Not found")
    return delivery

@router.get("/v1/dead-letter", response_model=PaginatedDeliveries)
async def list_dead_letter(request: Request, cursor: str | None = None, limit: int = Query(50, ge=1, le=200)):
    return await service.list_dead_letter(request.app.state.pool, cursor, limit)
