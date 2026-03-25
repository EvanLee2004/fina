"""
公司会计政策模型定义。

这个模块的目标不是把全部准则条文硬编码进系统，
而是先把“这家公司到底按哪套口径工作”固定下来。

当前主要解决三个问题：
1. 明确公司使用的是哪套会计准则。
2. 记录纳税人类型、币种和人工确认策略等关键口径。
3. 为 AI 记账和后续规则引擎提供稳定的政策上下文。
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Boolean, DateTime, Enum as SqlEnum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class AccountingStandard(str, Enum):
    """
    会计准则枚举。

    当前先覆盖你最关心的两套：
    - 小企业会计准则
    - 企业会计准则
    """

    SMALL_BUSINESS = "small_business"
    ENTERPRISE = "enterprise"


class TaxpayerType(str, Enum):
    """
    纳税人类型枚举。
    """

    SMALL_SCALE = "small_scale"
    GENERAL = "general"


class AccountingPolicy(Base):
    """
    公司会计政策 ORM 模型。

    当前系统按单公司模式工作，因此理论上只会维护一条主记录。
    这里仍然保留普通主键结构，避免未来做扩展时再返工表结构。
    """

    __tablename__ = "accounting_policies"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="会计政策主键 ID",
    )

    company_name: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
        comment="公司名称",
    )

    accounting_standard: Mapped[AccountingStandard | None] = mapped_column(
        SqlEnum(AccountingStandard, name="accounting_standard"),
        nullable=True,
        comment="会计准则类型：small_business 或 enterprise",
    )

    taxpayer_type: Mapped[TaxpayerType | None] = mapped_column(
        SqlEnum(TaxpayerType, name="taxpayer_type"),
        nullable=True,
        comment="纳税人类型：small_scale 或 general",
    )

    currency: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="CNY",
        comment="记账币种，默认 CNY",
    )

    standard_locked: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="是否锁定会计准则，锁定后不能随意切换",
    )

    require_manual_confirmation: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="AI 记账草稿是否必须人工确认",
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="补充政策说明，例如收入确认习惯、折旧口径等",
    )

    stripe_receipt_debit_account_id: Mapped[int | None] = mapped_column(
        ForeignKey("accounts.id"),
        nullable=True,
        comment="Stripe 收款默认借方科目 ID",
    )

    stripe_receipt_credit_account_id: Mapped[int | None] = mapped_column(
        ForeignKey("accounts.id"),
        nullable=True,
        comment="Stripe 收款默认贷方科目 ID",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="创建时间",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="更新时间",
    )
