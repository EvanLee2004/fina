"""
财务报告服务层。

这个文件专门负责：
1. 查询已存档的报告列表。
2. 查询指定月份报告。
3. 从凭证表汇总指定月份的收入、支出和净利润数据。
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from models.account import AccountType
from models.report import Report
from models.voucher import Voucher, VoucherEntry, VoucherStatus


def get_reports(db: Session) -> list[Report]:
    """
    查询所有报告列表。

    按报告期间倒序返回，方便优先查看最新月份。
    """
    statement = select(Report).order_by(Report.period.desc(), Report.id.desc())
    return list(db.scalars(statement).all())


def get_report_by_period(db: Session, period: str) -> Report:
    """
    查询指定月份报告。

    找不到对应月份时抛出 LookupError。
    """
    statement = select(Report).where(Report.period == period)
    report = db.scalar(statement)
    if report is None:
        raise LookupError("指定月份报告不存在。")
    return report


def generate_report(db: Session, period: str) -> dict[str, Decimal | str]:
    """
    汇总指定月份的财务数据。

    当前仅做数据汇总，不调用 AI，也不写入 reports 表。

    统计口径：
    - 只统计 approved 状态的凭证
    - 收入总额：收入类科目的贷方减借方
    - 支出总额：费用类和成本类科目的借方减贷方
    - 净利润：收入总额减支出总额
    """
    try:
        year, month = map(int, period.split("-"))
        start_date = date(year, month, 1)
    except ValueError as exc:
        raise ValueError("period 格式必须为 YYYY-MM。") from exc

    # 计算下一个月的月初日期，作为区间右边界。
    if month == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month + 1, 1)

    statement = (
        select(Voucher)
        .options(
            selectinload(Voucher.entries).selectinload(VoucherEntry.account)
        )
        .where(
            Voucher.status == VoucherStatus.APPROVED,
            Voucher.date >= start_date,
            Voucher.date < end_date,
        )
    )
    vouchers = list(db.scalars(statement).all())

    total_revenue = Decimal("0.00")
    total_expense = Decimal("0.00")

    for voucher in vouchers:
        for entry in voucher.entries:
            # 保护性判断：如果分录没有关联到账户对象，则跳过该分录。
            account = entry.account
            if account is None:
                continue

            if account.type == AccountType.REVENUE:
                total_revenue += entry.credit - entry.debit
            elif account.type in {AccountType.EXPENSE, AccountType.COST}:
                total_expense += entry.debit - entry.credit

    net_profit = total_revenue - total_expense

    return {
        "period": period,
        "total_revenue": total_revenue,
        "total_expense": total_expense,
        "net_profit": net_profit,
    }
