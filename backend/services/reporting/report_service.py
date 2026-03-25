"""
财务报告服务层。

本模块统一负责：
1. 计算客观财务数据。
2. 调用模型生成财务分析、风险提示和建议。
3. 把报告存档到 reports 表，供后续查询和导出复用。

设计原则：
- 所有数字先由代码计算，再交给模型分析。
- 模型不能编造数字，只能围绕给定数据做财务视角总结。
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from models.account import AccountType
from models.memory import Memory
from models.receivable import Receivable, ReceivableStatus, ReceivableType
from models.report import Report
from models.voucher import Voucher, VoucherEntry, VoucherStatus
from schemas.report import (
    AgingBucket,
    ExpenseBreakdownItem,
    FinancialNarrative,
    FinancialObjectiveSummary,
    FinancialReportResponse,
    MetricCard,
)
from services.agent.memory_service import format_memories_for_prompt, get_profile_memories
from services.integrations.llm_service import _call_ai_chat_completion, _extract_json_object


def _parse_period(period: str) -> tuple[date, date]:
    """
    把 YYYY-MM 转成闭开区间 [start_date, end_date)。
    """
    try:
        year, month = map(int, period.split("-"))
        start_date = date(year, month, 1)
    except ValueError as exc:
        raise ValueError("period 格式必须为 YYYY-MM。") from exc

    if month == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month + 1, 1)

    return start_date, end_date


def _build_aging_buckets(
    records: list[Receivable],
    kind: ReceivableType,
) -> list[AgingBucket]:
    """
    统计应收/应付账龄分布。

    这里的账龄按当前日期计算，采用简单且常用的 4 桶划分。
    """
    today = date.today()
    buckets = {
        "未到期": Decimal("0.00"),
        "1-30天": Decimal("0.00"),
        "31-90天": Decimal("0.00"),
        "90天以上": Decimal("0.00"),
    }

    for record in records:
        if record.type != kind or record.status != ReceivableStatus.PENDING:
            continue

        if record.due_date is None or record.due_date >= today:
            buckets["未到期"] += record.amount
            continue

        overdue_days = (today - record.due_date).days
        if overdue_days <= 30:
            buckets["1-30天"] += record.amount
        elif overdue_days <= 90:
            buckets["31-90天"] += record.amount
        else:
            buckets["90天以上"] += record.amount

    return [AgingBucket(label=label, amount=amount) for label, amount in buckets.items()]


def build_financial_objective_summary(db: Session, period: str) -> dict[str, Any]:
    """
    生成指定期间的客观财务汇总。

    这是整个报告、Excel、Word 导出的统一数据基础，
    保证所有对外交付物都使用同一套口径。
    """
    start_date, end_date = _parse_period(period)

    voucher_stmt = (
        select(Voucher)
        .options(selectinload(Voucher.entries).selectinload(VoucherEntry.account))
        .where(
            Voucher.status == VoucherStatus.APPROVED,
            Voucher.date >= start_date,
            Voucher.date < end_date,
        )
    )
    vouchers = list(db.scalars(voucher_stmt).all())

    receivable_stmt = select(Receivable).order_by(Receivable.created_at.desc())
    receivables = list(db.scalars(receivable_stmt).all())

    total_revenue = Decimal("0.00")
    total_expense = Decimal("0.00")
    pending_receivables = Decimal("0.00")
    pending_payables = Decimal("0.00")
    expense_breakdown_map: dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))

    for voucher in vouchers:
        for entry in voucher.entries:
            account = entry.account
            if account is None:
                continue

            if account.type == AccountType.REVENUE:
                total_revenue += entry.credit - entry.debit
            elif account.type in {AccountType.EXPENSE, AccountType.COST}:
                amount = entry.debit - entry.credit
                total_expense += amount
                expense_breakdown_map[account.name] += amount

    for item in receivables:
        if item.status != ReceivableStatus.PENDING:
            continue
        if item.type == ReceivableType.RECEIVABLE:
            pending_receivables += item.amount
        else:
            pending_payables += item.amount

    expense_breakdown = [
        ExpenseBreakdownItem(account_name=name, amount=amount)
        for name, amount in sorted(
            expense_breakdown_map.items(),
            key=lambda pair: pair[1],
            reverse=True,
        )[:8]
    ]

    net_profit = total_revenue - total_expense

    summary = FinancialObjectiveSummary(
        voucher_count=len(vouchers),
        total_revenue=total_revenue,
        total_expense=total_expense,
        net_profit=net_profit,
        pending_receivables=pending_receivables,
        pending_payables=pending_payables,
        expense_breakdown=expense_breakdown,
        receivable_aging=_build_aging_buckets(receivables, ReceivableType.RECEIVABLE),
        payable_aging=_build_aging_buckets(receivables, ReceivableType.PAYABLE),
    )

    return {
        "period": period,
        "summary": summary,
        "vouchers": vouchers,
        "receivables": receivables,
    }


def _build_metric_cards(summary: FinancialObjectiveSummary) -> list[MetricCard]:
    """
    生成顶部关键指标卡片。
    """
    return [
        MetricCard(label="收入", value=summary.total_revenue),
        MetricCard(label="支出", value=summary.total_expense),
        MetricCard(label="净利润", value=summary.net_profit),
        MetricCard(label="待收款", value=summary.pending_receivables),
        MetricCard(label="待付款", value=summary.pending_payables),
    ]


def _generate_ai_narrative(
    period: str,
    summary: FinancialObjectiveSummary,
    profile_memories: list[Memory],
    model: str | None = None,
) -> FinancialNarrative:
    """
    基于客观数据与公司画像生成 AI 财务分析。

    这里强制模型输出结构化 JSON，
    方便后端稳定地生成页面、Word 报告和聊天回复。
    """
    profile_text = format_memories_for_prompt(profile_memories)

    system_prompt = """
你是专业的财务分析顾问。
你的任务是基于客观财务数据输出一份管理层可读的财务总结。

严格要求：
1. 只能围绕给定数据和企业画像分析，不能编造数字。
2. 先做客观财务视角总结，再给风险与建议。
3. 输出必须是严格 JSON。

格式如下：
{
  "executive_summary": "一句到两句高层摘要",
  "analysis": "较完整的财务分析",
  "risks": ["风险1", "风险2"],
  "recommendations": ["建议1", "建议2"]
}
""".strip()

    user_prompt = f"""
报告期间：{period}

企业画像：
{profile_text}

客观财务数据：
凭证数量：{summary.voucher_count}
总收入：{summary.total_revenue}
总支出：{summary.total_expense}
净利润：{summary.net_profit}
待收款总额：{summary.pending_receivables}
待付款总额：{summary.pending_payables}
主要费用结构：{json.dumps([item.model_dump() for item in summary.expense_breakdown], ensure_ascii=False)}
应收账龄：{json.dumps([item.model_dump() for item in summary.receivable_aging], ensure_ascii=False)}
应付账龄：{json.dumps([item.model_dump() for item in summary.payable_aging], ensure_ascii=False)}
""".strip()

    content = _call_ai_chat_completion(system_prompt, user_prompt, model=model)
    parsed = _extract_json_object(content)

    return FinancialNarrative(
        executive_summary=str(parsed.get("executive_summary", "")).strip() or "暂无摘要。",
        analysis=str(parsed.get("analysis", "")).strip() or "暂无分析。",
        risks=[str(item).strip() for item in parsed.get("risks", []) if str(item).strip()],
        recommendations=[
            str(item).strip()
            for item in parsed.get("recommendations", [])
            if str(item).strip()
        ],
    )


def _render_report_content(
    period: str,
    summary: FinancialObjectiveSummary,
    narrative: FinancialNarrative,
) -> str:
    """
    生成一段可直接展示或写入 Word 的中文报告正文。
    """
    risk_lines = "\n".join([f"- {item}" for item in narrative.risks]) or "- 暂无明显风险提示"
    recommendation_lines = (
        "\n".join([f"- {item}" for item in narrative.recommendations]) or "- 暂无建议动作"
    )

    return f"""
{period} 财务报告

一、客观财务数据
- 凭证数量：{summary.voucher_count}
- 总收入：{summary.total_revenue}
- 总支出：{summary.total_expense}
- 净利润：{summary.net_profit}
- 待收款总额：{summary.pending_receivables}
- 待付款总额：{summary.pending_payables}

二、财务概览
{narrative.executive_summary}

三、财务分析
{narrative.analysis}

四、风险与异常
{risk_lines}

五、建议动作
{recommendation_lines}
""".strip()


def generate_financial_report(
    db: Session,
    memory_db: Session,
    period: str,
    model: str | None = None,
) -> FinancialReportResponse:
    """
    生成指定期间的完整财务报告，并同步归档到 reports 表。
    """
    objective_data = build_financial_objective_summary(db, period)
    summary: FinancialObjectiveSummary = objective_data["summary"]
    profile_memories = get_profile_memories(memory_db)
    narrative = _generate_ai_narrative(period, summary, profile_memories, model=model)
    content = _render_report_content(period, summary, narrative)

    objective_json = json.dumps(summary.model_dump(mode="json"), ensure_ascii=False)

    existing_report = db.scalar(select(Report).where(Report.period == period))
    if existing_report is None:
        report = Report(period=period, content=content, objective_json=objective_json)
        db.add(report)
    else:
        existing_report.content = content
        existing_report.objective_json = objective_json
        report = existing_report

    db.commit()
    db.refresh(report)

    return FinancialReportResponse(
        period=period,
        metrics=_build_metric_cards(summary),
        objective_summary=summary,
        narrative=narrative,
        content=content,
    )


def get_reports(db: Session) -> list[Report]:
    """
    获取已归档报告列表。
    """
    stmt = select(Report).order_by(Report.period.desc(), Report.id.desc())
    return list(db.scalars(stmt).all())


def get_report_by_period(
    db: Session,
    memory_db: Session,
    period: str,
    model: str | None = None,
) -> FinancialReportResponse:
    """
    获取指定月份报告。

    当前策略是：
    - 如果已有归档，仍然重新按当前数据生成，保证结果最新
    - 同时覆盖归档内容，避免旧报告长期过期
    """
    return generate_financial_report(db=db, memory_db=memory_db, period=period, model=model)
