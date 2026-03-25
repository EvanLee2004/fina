"""
Stripe webhook 路由。

这个接口不走管理员令牌，而是依赖 Stripe 官方签名校验来确认来源。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from core.database import get_db
from services.integrations.stripe_service import construct_stripe_event, process_stripe_event

router = APIRouter(
    prefix="/api/integrations/stripe",
    tags=["Stripe"],
)


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    """
    接收 Stripe webhook 事件。
    """
    payload = await request.body()
    signature = request.headers.get("Stripe-Signature")

    try:
        event = construct_stripe_event(payload, signature)
        return process_stripe_event(db, event)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"处理 Stripe 事件失败：{exc}",
        ) from exc
