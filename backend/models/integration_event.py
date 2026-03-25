"""
外部集成事件模型。

这张表的目的有两个：
1. 记录来自 Stripe 等外部系统的异步事件，便于追溯。
2. 通过 event_id 唯一约束做幂等控制，避免同一个 webhook 重复触发重复记账。
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class IntegrationEvent(Base):
    """
    外部集成事件 ORM 模型。
    """

    __tablename__ = "integration_events"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="集成事件主键 ID",
    )

    provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="事件来源，例如 stripe",
    )

    event_id: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        unique=True,
        index=True,
        comment="外部系统事件 ID，用于幂等去重",
    )

    event_type: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        index=True,
        comment="事件类型，例如 payment_intent.succeeded",
    )

    status: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default="received",
        comment="处理状态，例如 received / processed / ignored / failed / duplicated",
    )

    payload_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="原始事件 JSON",
    )

    result_json: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="处理结果 JSON，例如生成的凭证草稿或忽略原因",
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="处理失败时的错误信息",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="事件入库时间",
    )

    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="事件处理完成时间",
    )
