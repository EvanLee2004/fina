"""
Stripe 集成服务。

这里把 Stripe webhook 的关键逻辑集中起来：
1. 校验 webhook 签名。
2. 做事件幂等控制。
3. 把支付事件转换为可记账的业务描述。
4. 复用现有 AI 记账链路生成凭证草稿。
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import stripe
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.config import settings
from models.accounting_policy import AccountingPolicy
from models.integration_event import IntegrationEvent
from schemas.voucher import VoucherCreate, VoucherEntryCreate
from services.accounting.voucher_service import approve_voucher, create_voucher


def _amount_to_decimal(amount: int | None, currency: str | None) -> Decimal:
    """
    把 Stripe 的最小货币单位金额转为常见金额表示。

    Stripe 的金额通常以最小货币单位传输，例如分。
    这里先按两位小数货币处理，满足当前人民币/美元等主场景。
    """
    if amount is None:
        return Decimal("0.00")
    normalized = Decimal(str(amount)) / Decimal("100")
    return normalized.quantize(Decimal("0.01"))


def construct_stripe_event(payload: bytes, signature: str | None) -> stripe.Event:
    """
    使用 Stripe 官方 SDK 校验签名并构造事件对象。
    """
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise ValueError("STRIPE_WEBHOOK_SECRET 未配置，无法校验 Stripe webhook。")

    if not signature:
        raise ValueError("缺少 Stripe-Signature 请求头。")

    try:
        return stripe.Webhook.construct_event(
            payload=payload,
            sig_header=signature,
            secret=settings.STRIPE_WEBHOOK_SECRET,
        )
    except ValueError as exc:
        raise ValueError("Stripe webhook payload 不是合法 JSON。") from exc
    except stripe.error.SignatureVerificationError as exc:
        raise ValueError("Stripe webhook 签名校验失败。") from exc


def _build_payment_intent_message(payment_intent: dict[str, Any]) -> str:
    """
    把 Stripe PaymentIntent 转成适合交给 AI 记账的中文业务描述。
    """
    amount = _amount_to_decimal(
        payment_intent.get("amount_received") or payment_intent.get("amount"),
        payment_intent.get("currency"),
    )
    currency = str(payment_intent.get("currency", "cny")).upper()
    description = payment_intent.get("description") or "未填写"
    customer = payment_intent.get("customer") or "未识别客户"
    metadata = payment_intent.get("metadata") or {}
    order_no = metadata.get("order_id") or metadata.get("order_no") or "未提供"
    created_ts = payment_intent.get("created")
    created_text = datetime.fromtimestamp(created_ts, tz=timezone.utc).date().isoformat() if created_ts else datetime.now(timezone.utc).date().isoformat()

    return (
        f"{created_text}，Stripe 回款成功，收到一笔银行卡付款。"
        f"金额 {amount} {currency}，PaymentIntent 为 {payment_intent.get('id')}，"
        f"客户标识 {customer}，订单号 {order_no}，业务说明 {description}。"
        "这是一条来自支付网关的自动回款事件。"
    )


def _serialize_event(event: stripe.Event) -> str:
    """
    将 Stripe 事件序列化为 JSON，便于落库审计。
    """
    return json.dumps(event.to_dict_recursive(), ensure_ascii=False)


def process_stripe_event(
    db: Session,
    event: stripe.Event,
    model: str | None = None,
) -> dict[str, Any]:
    """
    处理 Stripe 事件，并在适用场景下生成凭证草稿。
    """
    existing = db.scalar(
        select(IntegrationEvent).where(IntegrationEvent.event_id == event.id)
    )
    if existing is not None:
        return {
            "status": "duplicated",
            "event_id": event.id,
            "event_type": event.type,
            "message": "该 Stripe 事件已处理过，已按幂等规则忽略。",
        }

    integration_event = IntegrationEvent(
        provider="stripe",
        event_id=event.id,
        event_type=event.type,
        status="received",
        payload_json=_serialize_event(event),
    )
    db.add(integration_event)
    db.commit()
    db.refresh(integration_event)

    try:
        if event.type != "payment_intent.succeeded":
            result = {
                "status": "ignored",
                "event_id": event.id,
                "event_type": event.type,
                "message": "当前只对 payment_intent.succeeded 做自动记账草稿处理。",
            }
            integration_event.status = "ignored"
            integration_event.result_json = json.dumps(result, ensure_ascii=False)
            integration_event.processed_at = datetime.now(timezone.utc)
            db.commit()
            return result

        payment_intent = event.data.object
        message = _build_payment_intent_message(payment_intent)
        policy = db.scalar(select(AccountingPolicy).order_by(AccountingPolicy.id.asc()))
        if policy is None or policy.accounting_standard is None:
            raise ValueError("当前尚未配置会计政策，不能对 Stripe 回款做自动记账。")

        if (
            policy.stripe_receipt_debit_account_id is None
            or policy.stripe_receipt_credit_account_id is None
        ):
            raise ValueError(
                "当前尚未配置 Stripe 自动记账科目映射，请先设置借方和贷方科目。"
            )

        created_ts = payment_intent.get("created")
        voucher_date = (
            datetime.fromtimestamp(created_ts, tz=timezone.utc).date()
            if created_ts
            else datetime.now(timezone.utc).date()
        )
        amount = _amount_to_decimal(
            payment_intent.get("amount_received") or payment_intent.get("amount"),
            payment_intent.get("currency"),
        )
        draft = VoucherCreate(
            date=voucher_date,
            memo=f"Stripe 收款 {payment_intent.get('id')}",
            entries=[
                VoucherEntryCreate(
                    account_id=policy.stripe_receipt_debit_account_id,
                    debit=amount,
                    credit=Decimal("0.00"),
                ),
                VoucherEntryCreate(
                    account_id=policy.stripe_receipt_credit_account_id,
                    debit=Decimal("0.00"),
                    credit=amount,
                ),
            ],
        )
        voucher = create_voucher(db, draft)
        if not policy.require_manual_confirmation:
            voucher = approve_voucher(db, voucher.id)

        result = {
            "status": "processed",
            "event_id": event.id,
            "event_type": event.type,
            "message": message,
            "voucher_id": voucher.id,
            "voucher_status": voucher.status.value,
            "draft": draft.model_dump(mode="json"),
        }
        integration_event.status = "processed"
        integration_event.result_json = json.dumps(result, ensure_ascii=False, default=str)
        integration_event.processed_at = datetime.now(timezone.utc)
        db.commit()
        return result
    except Exception as exc:
        integration_event.status = "failed"
        integration_event.error_message = str(exc)
        integration_event.processed_at = datetime.now(timezone.utc)
        db.commit()
        raise
