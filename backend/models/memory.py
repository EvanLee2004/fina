"""
长期记忆模型定义。

两层记忆架构：
- profile: 企业背景、经营特征、固定规则等“公司画像”
- long_term: 从对话和业务中沉淀下来的长期知识

这些数据统一放在独立记忆库中。
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import DateTime, Enum as SqlEnum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.memory_database import MemoryBase


class MemoryType(str, Enum):
    """记忆类型枚举。"""

    # 企业画像：主营业务、经营模式、关键客户结构、内部口径等。
    # 这类信息相对稳定，因此每次对话都会加载。
    PROFILE = "profile"

    # 长期记忆：从对话和交易中提炼出的长期可复用知识。
    # 这类信息只在相关场景下按需检索。
    LONG_TERM = "long_term"


class Memory(MemoryBase):
    """长期记忆 ORM 模型。"""

    __tablename__ = "memories"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True,
    )

    # 记忆类型：profile 或 long_term。
    type: Mapped[MemoryType] = mapped_column(
        SqlEnum(MemoryType, name="memory_type"),
        nullable=False, index=True,
        comment="记忆类型",
    )

    # 记忆分类标签，便于检索和管理。
    # 例如："企业信息"、"客户_张三"、"费用规律"、"税务"
    category: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True,
        comment="记忆分类标签",
    )

    # 记忆内容，纯文本。
    content: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="记忆内容",
    )

    # 来源说明，记录这条记忆从哪次对话或事件中产生。
    source: Mapped[str | None] = mapped_column(
        String(255), nullable=True,
        comment="记忆来源，例如 conversation:123",
    )

    # 重要性评分。
    # 每条长期记忆都带一个 1-5 的重要性等级，方便后续筛选高价值知识。
    importance: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=3,
        comment="重要性评分，范围 1-5",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
