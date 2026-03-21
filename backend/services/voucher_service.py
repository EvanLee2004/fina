"""
凭证服务层。

这个文件专门负责：
1. 查询凭证列表和单条凭证详情，并预加载分录数据。
2. 新增凭证及其分录。
3. 严格校验借贷平衡。
4. 处理凭证审核和删除的状态规则。
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from models.voucher import Voucher, VoucherEntry, VoucherStatus

# 当前项目还没有从 X-Admin-Token 中解析出管理员身份，
# 因此先使用固定占位值作为创建人标识。
# 后续接入外部管理员上下文后，再替换为真实的 admin/user id。
DEFAULT_CREATED_BY = 0


def _validate_entries_balance(entries: list) -> None:
    """
    校验分录借贷是否平衡。

    规则：
    - 分录列表不能为空
    - 所有借方总额必须严格等于贷方总额
    """
    if not entries:
        raise ValueError("凭证至少需要一条分录。")

    total_debit = sum((entry.debit for entry in entries), Decimal("0.00"))
    total_credit = sum((entry.credit for entry in entries), Decimal("0.00"))

    # 借贷平衡是记账核心规则，这里必须严格相等。
    if total_debit != total_credit:
        raise ValueError("借贷不平衡：所有分录借方总额必须等于贷方总额。")


def get_vouchers(
    db: Session,
    start_date: date | None,
    end_date: date | None,
) -> list[Voucher]:
    """
    查询凭证列表。

    支持按日期范围筛选，并预加载 entries，避免后续序列化时出现 N+1 查询。
    """
    statement = (
        select(Voucher)
        .options(selectinload(Voucher.entries))
        .order_by(Voucher.date.desc(), Voucher.id.desc())
    )

    if start_date is not None:
        statement = statement.where(Voucher.date >= start_date)

    if end_date is not None:
        statement = statement.where(Voucher.date <= end_date)

    return list(db.scalars(statement).all())


def get_voucher(db: Session, voucher_id: int) -> Voucher:
    """
    查询单条凭证详情，并携带分录列表。

    找不到凭证时抛出 LookupError。
    """
    statement = (
        select(Voucher)
        .options(selectinload(Voucher.entries))
        .where(Voucher.id == voucher_id)
    )
    voucher = db.scalar(statement)
    if voucher is None:
        raise LookupError("凭证不存在。")
    return voucher


def create_voucher(db: Session, data) -> Voucher:
    """
    新增凭证及其分录。

    核心校验：
    - 分录不能为空
    - 借贷必须严格平衡
    """
    _validate_entries_balance(data.entries)

    voucher = Voucher(
        date=data.date,
        memo=data.memo,
        status=VoucherStatus.DRAFT,
        created_by=DEFAULT_CREATED_BY,
    )

    for entry in data.entries:
        voucher.entries.append(
            VoucherEntry(
                account_id=entry.account_id,
                debit=entry.debit,
                credit=entry.credit,
            )
        )

    db.add(voucher)
    db.commit()
    db.refresh(voucher)
    return get_voucher(db, voucher.id)


def approve_voucher(db: Session, voucher_id: int) -> Voucher:
    """
    审核指定凭证。

    规则：
    - 只能审核存在的凭证
    - 已审核凭证不能重复审核
    """
    voucher = db.get(Voucher, voucher_id)
    if voucher is None:
        raise LookupError("凭证不存在。")

    if voucher.status == VoucherStatus.APPROVED:
        raise ValueError("已审核凭证不能重复审核。")

    voucher.status = VoucherStatus.APPROVED
    db.commit()
    db.refresh(voucher)
    return get_voucher(db, voucher.id)


def delete_voucher(db: Session, voucher_id: int) -> None:
    """
    删除指定凭证。

    规则：
    - 找不到凭证时抛出 LookupError
    - 只有 draft 状态的凭证允许删除
    """
    voucher = db.get(Voucher, voucher_id)
    if voucher is None:
        raise LookupError("凭证不存在。")

    if voucher.status != VoucherStatus.DRAFT:
        raise ValueError("已审核凭证不能删除。")

    db.delete(voucher)
    db.commit()
