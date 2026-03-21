"""
凭证表与凭证分录表模型定义。

这个文件的职责是：
1. 定义凭证主表 vouchers。
2. 定义凭证分录表 voucher_entries。
3. 通过一对多关系表达“一张凭证包含多条分录”。
4. 在删除凭证时级联删除对应分录，保证数据一致性。
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum

from sqlalchemy import Date, DateTime, Enum as SqlEnum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class VoucherStatus(str, Enum):
    """
    凭证状态枚举。

    这里使用 Python 枚举来约束 status 字段，
    避免业务代码中出现不受控的状态字符串。
    """

    # 草稿状态。
    # 说明凭证还处于编辑阶段，尚未正式审核通过。
    DRAFT = "draft"

    # 已审核状态。
    # 说明凭证已经通过审核，可以参与后续账务统计和报表计算。
    APPROVED = "approved"


class Voucher(Base):
    """
    凭证主表 ORM 模型。

    这个模型会映射到 PostgreSQL 中的 vouchers 表。
    一张凭证对应多条凭证分录，用来记录完整的借贷分录信息。
    """

    # 指定数据库中的表名。
    __tablename__ = "vouchers"

    # 凭证主键 ID。
    # 使用自增整数作为内部主键，便于和分录表做外键关联。
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="凭证主键 ID",
    )

    # 凭证日期。
    # 表示该凭证所属的业务日期或记账日期。
    date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
        comment="凭证日期",
    )

    # 凭证摘要。
    # 用于简要说明这张凭证对应的业务内容，例如“支付房租”。
    memo: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="凭证摘要",
    )

    # 凭证状态。
    # 使用数据库枚举字段与 Python 枚举绑定，只允许 draft / approved。
    status: Mapped[VoucherStatus] = mapped_column(
        SqlEnum(VoucherStatus, name="voucher_status"),
        nullable=False,
        default=VoucherStatus.DRAFT,
        comment="凭证状态，限定为 draft 或 approved",
    )

    # 创建人 ID。
    # 由于当前项目不再维护本地 users 表，
    # 这里保留一个普通整数字段，用于记录外部管理平台中的创建人标识。
    created_by: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
        comment="创建人标识，由外部管理平台提供",
    )

    # 凭证创建时间。
    # 默认记录当前 UTC 时间，便于审计与时间排序。
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="凭证创建时间",
    )

    # 凭证分录列表。
    # 一张凭证可以有多条分录，因此这里是一对多关系。
    # cascade=\"all, delete-orphan\" 表示删除凭证时，会自动删除其所属分录。
    entries: Mapped[list["VoucherEntry"]] = relationship(
        "VoucherEntry",
        back_populates="voucher",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

class VoucherEntry(Base):
    """
    凭证分录表 ORM 模型。

    这个模型会映射到 PostgreSQL 中的 voucher_entries 表。
    每条分录对应一个会计科目，并记录借方金额或贷方金额。
    """

    # 指定数据库中的表名。
    __tablename__ = "voucher_entries"

    # 分录主键 ID。
    # 使用自增整数作为内部主键，便于单独查询和维护。
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="凭证分录主键 ID",
    )

    # 所属凭证 ID。
    # 该字段关联 vouchers.id，用于把多条分录归属于同一张凭证。
    # ondelete=\"CASCADE\" 保证数据库层面删除凭证时，分录也会被一并删除。
    voucher_id: Mapped[int] = mapped_column(
        ForeignKey("vouchers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属凭证 ID，关联 vouchers.id",
    )

    # 会计科目 ID。
    # 该字段关联 accounts.id，用于标识本条分录记入哪个会计科目。
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id"),
        nullable=False,
        index=True,
        comment="会计科目 ID，关联 accounts.id",
    )

    # 借方金额。
    # 使用 Numeric(10, 2) 保证金额总精度 10 位，小数 2 位。
    # 默认值为 0.00，便于业务层只填写借方或贷方其中一侧。
    debit: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=Decimal("0.00"),
        comment="借方金额，精度 10 位，小数 2 位",
    )

    # 贷方金额。
    # 使用 Numeric(10, 2) 保证金额总精度 10 位，小数 2 位。
    # 默认值为 0.00，便于业务层只填写借方或贷方其中一侧。
    credit: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=Decimal("0.00"),
        comment="贷方金额，精度 10 位，小数 2 位",
    )

    # 所属凭证对象。
    # 通过这个关系可以从分录回到对应的凭证主表记录。
    voucher: Mapped["Voucher"] = relationship(
        "Voucher",
        back_populates="entries",
    )

    # 关联科目对象。
    # 通过这个关系可以直接访问本条分录对应的会计科目信息。
    account: Mapped["Account"] = relationship("Account")
