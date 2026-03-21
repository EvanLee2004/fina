"""
应收应付表模型定义。

这个文件的职责是：
1. 定义统一的往来款项表 receivables。
2. 同时表示应收款和应付款两类业务数据。
3. 为后续账期跟踪、核销、提醒等功能提供 ORM 模型。
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum

from sqlalchemy import Date, DateTime, Enum as SqlEnum, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class ReceivableType(str, Enum):
    """
    往来款项类型枚举。

    这里使用 Python 枚举来约束 type 字段，
    避免业务代码中出现不受控的字符串。
    """

    # 应收款。
    # 表示别人欠平台或企业的钱，例如客户应收账款。
    RECEIVABLE = "receivable"

    # 应付款。
    # 表示平台或企业需要支付给别人的款项，例如供应商应付款。
    PAYABLE = "payable"


class ReceivableStatus(str, Enum):
    """
    往来款项状态枚举。

    用于标识当前款项是否已经完成结清。
    """

    # 待处理状态。
    # 表示该笔应收或应付还没有结清。
    PENDING = "pending"

    # 已结清状态。
    # 表示该笔应收或应付已经完成收款或付款。
    SETTLED = "settled"


class Receivable(Base):
    """
    应收应付 ORM 模型。

    这个模型会映射到 PostgreSQL 中的 receivables 表。
    后续列表查询、账期提醒、结清处理等功能都会依赖这张表。
    """

    # 指定数据库中的表名。
    __tablename__ = "receivables"

    # 主键 ID。
    # 使用自增整数作为内部主键，便于查询、更新和关联。
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="应收应付主键 ID",
    )

    # 往来款项类型。
    # 只允许 receivable 或 payable 两种值。
    type: Mapped[ReceivableType] = mapped_column(
        SqlEnum(ReceivableType, name="receivable_type"),
        nullable=False,
        comment="往来款项类型，限定为 receivable 或 payable",
    )

    # 往来单位名称。
    # 用于记录客户、供应商或其他对手方名称。
    party: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="往来单位名称",
    )

    # 金额。
    # 使用 Numeric(10, 2) 保证金额总精度 10 位，小数 2 位。
    amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="往来金额，精度 10 位，小数 2 位",
    )

    # 到期日。
    # 某些往来款没有明确账期，因此该字段允许为空。
    due_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        index=True,
        comment="到期日，可为空",
    )

    # 当前状态。
    # 用于标识这笔款项是否已经结清。
    status: Mapped[ReceivableStatus] = mapped_column(
        SqlEnum(ReceivableStatus, name="receivable_status"),
        nullable=False,
        default=ReceivableStatus.PENDING,
        comment="款项状态，限定为 pending 或 settled",
    )

    # 备注。
    # 用于补充说明业务背景、合同信息、结算说明等内容。
    memo: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="备注信息，可为空",
    )

    # 创建时间。
    # 默认记录当前 UTC 时间，便于排序和审计。
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="创建时间",
    )
