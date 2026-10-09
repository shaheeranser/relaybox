"""HTTP endpoints for /v1/subscriptions."""
from __future__ import annotations
from fastapi import APIRouter, Depends, Request, HTTPException
from app.auth import verify_token
from app.models import CreateSubscription, UpdateSubscription, SubscriptionOut
from app.subscriptions import service

router = APIRouter(prefix="/v1/subscriptions", tags=["subscriptions"], dependencies=[Depends(verify_token)])

@router.post("", response_model=SubscriptionOut)
async def create(request: Request, data: CreateSubscription):
    return await service.create_subscription(request.app.state.pool, data)

@router.get("", response_model=list[SubscriptionOut])
async def list_all(request: Request):
    return await service.list_subscriptions(request.app.state.pool)

@router.get("/{id}", response_model=SubscriptionOut)
async def get(request: Request, id: str):
    sub = await service.get_subscription(request.app.state.pool, id)
    if not sub:
        raise HTTPException(status_code=404, detail="Not found")
    return sub

@router.patch("/{id}", response_model=SubscriptionOut)
async def update(request: Request, id: str, data: UpdateSubscription):
    sub = await service.update_subscription(request.app.state.pool, id, data)
    if not sub:
        raise HTTPException(status_code=404, detail="Not found")
    return sub

@router.delete("/{id}", status_code=204)
async def delete(request: Request, id: str):
    deleted = await service.delete_subscription(request.app.state.pool, id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Not found")
