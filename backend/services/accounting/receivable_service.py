"""
应收应付服务层。

这个文件专门负责：
1. 查询应收应付列表，并支持按类型和状态筛选。
2. 新增应收应付记录。
3. 处理结清状态流转。
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.receivable import Receivable, ReceivableStatus, ReceivableType


def get_receivables(
    db: Session,
    type: ReceivableType | None,
    status: ReceivableStatus | None,
) -> list[Receivable]:
    """
    查询应收应付列表。

    支持按 type 和 status 做可选筛选，
    并按创建时间倒序返回，便于优先看到最新记录。
    """
    statement = select(Receivable).order_by(
        Receivable.created_at.desc(),
        Receivable.id.desc(),
    )

    if type is not None:
        statement = statement.where(Receivable.type == type)

    if status is not None:
        statement = statement.where(Receivable.status == status)

    return list(db.scalars(statement).all())


def create_receivable(db: Session, data) -> Receivable:
    """
    新增一条应收应付记录。

    新建记录时默认状态为 pending，
    表示该笔款项尚未结清。
    """
    receivable = Receivable(
        type=data.type,
        party=data.party,
        amount=data.amount,
        due_date=data.due_date,
        status=ReceivableStatus.PENDING,
        memo=data.memo,
    )
    db.add(receivable)
    db.commit()
    db.refresh(receivable)
    return receivable


def settle_receivable(db: Session, receivable_id: int) -> Receivable:
    """
    将指定应收应付记录标记为已结清。

    规则：
    - 找不到记录时抛出 LookupError
    - 已结清的记录不能重复结清
    """
    receivable = db.get(Receivable, receivable_id)
    if receivable is None:
        raise LookupError("应收应付记录不存在。")

    if receivable.status == ReceivableStatus.SETTLED:
        raise ValueError("该记录已经结清，不能重复操作。")

    receivable.status = ReceivableStatus.SETTLED
    db.commit()
    db.refresh(receivable)
    return receivable
