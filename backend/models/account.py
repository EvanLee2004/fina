"""
会计科目表模型定义。

这个文件的职责是：
1. 定义系统中的会计科目表 accounts。
2. 约束科目类型，只允许资产、负债、所有者权益、收入、成本、费用六大类。
3. 通过 parent_id 关联自身表，支持多级科目结构。
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Boolean, DateTime, Enum as SqlEnum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class AccountType(str, Enum):
    """
    会计科目类型枚举。

    这里使用 Python 枚举来约束 type 字段，
    避免业务代码里散落不受控的字符串。
    """

    # 资产类科目，例如库存现金、银行存款、应收账款。
    ASSET = "asset"

    # 负债类科目，例如应付账款、应交税费。
    LIABILITY = "liability"

    # 所有者权益类科目，例如实收资本、未分配利润。
    EQUITY = "equity"

    # 收入类科目，例如主营业务收入、其他业务收入。
    REVENUE = "revenue"

    # 成本类科目，例如主营业务成本、生产成本。
    COST = "cost"

    # 费用类科目，例如管理费用、销售费用、财务费用。
    EXPENSE = "expense"


class Account(Base):
    """
    会计科目 ORM 模型。

    这个模型会映射到 PostgreSQL 中的 accounts 表。
    后续凭证录入、报表统计、科目树展示都会依赖这张表。
    """

    # 指定数据库中的表名。
    __tablename__ = "accounts"

    # 科目主键 ID。
    # 使用自增整数作为内部主键，便于做外键关联和树形查询。
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="科目主键 ID",
    )

    # 科目编码。
    # 编码在会计系统里通常具有业务含义，因此设置为唯一值，避免重复。
    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="科目编码，例如 1001、2202",
    )

    # 科目名称。
    # 用于页面展示和业务录入时识别科目。
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="科目名称，例如 库存现金、应付账款",
    )

    # 科目类型。
    # 使用数据库枚举字段与 Python 枚举绑定，限定六大科目类型。
    type: Mapped[AccountType] = mapped_column(
        SqlEnum(AccountType, name="account_type"),
        nullable=False,
        comment="科目类型，限定为 asset、liability、equity、revenue、cost、expense",
    )

    # 父科目 ID。
    # 该字段指向同一张 accounts 表的主键，用于构建多级科目树。
    # 顶级科目没有父级，因此允许为空。
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("accounts.id"),
        nullable=True,
        index=True,
        comment="父科目 ID，可为空，指向 accounts.id",
    )

    # 科目是否启用。
    # 如果某个科目停用，可以通过该字段阻止新业务继续使用它。
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="科目是否启用，False 表示停用",
    )

    # 科目创建时间。
    # 默认记录当前 UTC 时间，便于审计和后续排序。
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="科目创建时间",
    )

    # 父科目对象。
    # remote_side=[id] 用来告诉 SQLAlchemy：这是一个指向自身主键的自关联关系。
    parent: Mapped["Account | None"] = relationship(
        "Account",
        remote_side=[id],
        back_populates="children",
    )

    # 子科目列表。
    # 一个父科目下面可以挂多个子科目，因此这里是一对多关系。
    children: Mapped[list["Account"]] = relationship(
        "Account",
        back_populates="parent",
        cascade="save-update, merge",
    )
