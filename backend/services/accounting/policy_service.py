"""
公司会计政策服务层。

这个模块负责：
1. 获取当前公司会计政策。
2. 更新会计政策。
3. 执行“会计准则锁定”规则，避免后续随意切换口径。
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.accounting_policy import AccountingPolicy


def get_accounting_policy(db: Session) -> AccountingPolicy | None:
    """
    获取当前公司会计政策。

    单公司模式下，默认取主键最小的一条记录作为当前生效政策。
    """
    stmt = select(AccountingPolicy).order_by(AccountingPolicy.id.asc())
    return db.scalar(stmt)


def upsert_accounting_policy(db: Session, payload) -> AccountingPolicy:
    """
    新增或更新公司会计政策。

    关键规则：
    - 如果已经设置了会计准则且标准被锁定，则不允许直接切换。
    - 这样可以避免系统今天按小企业准则、明天又按企业准则解释同一笔业务。
    """
    policy = get_accounting_policy(db)
    if policy is None:
        policy = AccountingPolicy()
        db.add(policy)

    requested_standard = payload.accounting_standard
    if (
        requested_standard is not None
        and policy.accounting_standard is not None
        and policy.standard_locked
        and requested_standard != policy.accounting_standard
    ):
        raise ValueError(
            "当前会计准则已锁定，不能直接切换。若确需切换，请先显式解除锁定并完成人工复核。"
        )

    for field_name in [
        "company_name",
        "accounting_standard",
        "taxpayer_type",
        "currency",
        "standard_locked",
        "require_manual_confirmation",
        "notes",
        "stripe_receipt_debit_account_id",
        "stripe_receipt_credit_account_id",
    ]:
        field_value = getattr(payload, field_name)
        if field_value is not None:
            setattr(policy, field_name, field_value)

    db.commit()
    db.refresh(policy)
    return policy
