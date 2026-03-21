"""
AI 服务层。

这个文件专门负责：
1. 调用 DeepSeek API 做自然语言记账解析。
2. 按月份汇总凭证数据并生成 AI 财务分析报告。
3. 处理自然语言财务查询。
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from core.config import settings
from models.account import Account, AccountType
from models.report import Report
from models.voucher import Voucher, VoucherEntry, VoucherStatus

DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"


def _call_deepseek(system_prompt: str, user_prompt: str) -> str:
    """
    调用 DeepSeek 聊天补全接口。

    返回值只取第一条消息内容，
    由上层函数决定如何解析成 JSON 或普通文本。
    """
    if not settings.DEEPSEEK_API_KEY:
        raise ValueError("DEEPSEEK_API_KEY 未配置。")

    payload = {
        "model": DEEPSEEK_MODEL,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }

    with httpx.Client(timeout=60.0) as client:
        response = client.post(
            DEEPSEEK_API_URL,
            headers={
                "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()

    response_data = response.json()
    try:
        return response_data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("DeepSeek 返回结果格式异常。") from exc


def _extract_json_object(content: str) -> dict[str, Any]:
    """
    从模型返回内容中提取 JSON 对象。

    即使模型错误地包了一层 Markdown 代码块，
    这里也尽量做容错解析。
    """
    cleaned = content.strip()

    # 去掉可能的 ```json ... ``` 包裹。
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError("AI 返回内容不是合法 JSON。") from exc

    if not isinstance(parsed, dict):
        raise ValueError("AI 返回的 JSON 顶层必须是对象。")

    return parsed


def _validate_balance(entries: list[dict[str, Any]]) -> None:
    """
    校验凭证草稿分录借贷是否平衡。

    这是自然语言记账结果进入确认流程前的核心校验。
    """
    if not entries:
        raise ValueError("AI 返回的分录列表不能为空。")

    total_debit = sum((Decimal(str(entry["debit"])) for entry in entries), Decimal("0.00"))
    total_credit = sum((Decimal(str(entry["credit"])) for entry in entries), Decimal("0.00"))

    if total_debit != total_credit:
        raise ValueError("AI 解析结果借贷不平衡。")


def _build_accounts_prompt(db: Session) -> str:
    """
    读取所有启用中的科目，并格式化为 Prompt 文本。

    Prompt 中会携带完整科目表，
    让模型只能从现有科目中选择 account_id。
    """
    statement = (
        select(Account)
        .where(Account.is_active.is_(True))
        .order_by(Account.code.asc(), Account.id.asc())
    )
    accounts = list(db.scalars(statement).all())

    if not accounts:
        raise ValueError("当前没有可用的启用科目，无法进行 AI 记账。")

    lines = []
    for account in accounts:
        lines.append(
            f"id={account.id}, code={account.code}, name={account.name}, type={account.type.value}"
        )
    return "\n".join(lines)


def _summarize_period_metrics(db: Session, period: str) -> dict[str, Any]:
    """
    汇总指定月份已审核凭证的核心财务数据。

    统计字段：
    - total_revenue: 收入总额
    - total_expense: 支出总额（费用类 + 成本类）
    - net_profit: 净利润
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

    statement = (
        select(Voucher)
        .options(selectinload(Voucher.entries).selectinload(VoucherEntry.account))
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
        "voucher_count": len(vouchers),
        "total_revenue": total_revenue,
        "total_expense": total_expense,
        "net_profit": net_profit,
    }


def _infer_period_from_text(text: str) -> str:
    """
    从自然语言中推断查询月份。

    当前支持：
    - 显式 YYYY-MM
    - 本月 / 这个月
    - 上个月
    未命中时默认按当前月份处理。
    """
    match = re.search(r"\b(\d{4}-\d{2})\b", text)
    if match:
        return match.group(1)

    today = date.today()

    if "上个月" in text:
        if today.month == 1:
            return f"{today.year - 1}-12"
        return f"{today.year}-{today.month - 1:02d}"

    if "本月" in text or "这个月" in text:
        return f"{today.year}-{today.month:02d}"

    return f"{today.year}-{today.month:02d}"


def parse_natural_language(db: Session, text: str) -> dict[str, Any]:
    """
    将自然语言描述解析为凭证草稿。

    流程：
    1. 读取完整科目表
    2. 组织 Prompt 调用 DeepSeek
    3. 解析并校验模型返回的严格 JSON
    4. 校验借贷平衡后返回草稿，不写入数据库
    """
    accounts_prompt = _build_accounts_prompt(db)

    system_prompt = (
        "你是专业会计助手。"
        "你必须根据提供的完整科目表，把用户的中文业务描述解析成会计凭证草稿。"
        "你只能返回严格 JSON，不要返回解释、Markdown、代码块或任何多余文字。"
        "回答必须使用中文语境。"
    )

    user_prompt = f"""
今天日期：{date.today().isoformat()}

完整科目表如下：
{accounts_prompt}

用户输入：
{text}

请只返回严格 JSON，格式必须完全如下：
{{
  "date": "2026-03-21",
  "memo": "摘要",
  "entries": [
    {{
      "account_id": 1,
      "debit": 3000,
      "credit": 0
    }}
  ]
}}

要求：
1. account_id 必须只能使用上面科目表里已有的 id
2. entries 至少两条，且必须借贷平衡
3. 不确定时优先生成最保守、最常见的会计处理
4. 只返回 JSON，不要任何其他文字
""".strip()

    content = _call_deepseek(system_prompt, user_prompt)
    parsed = _extract_json_object(content)

    required_keys = {"date", "memo", "entries"}
    if not required_keys.issubset(parsed.keys()):
        raise ValueError("AI 返回的 JSON 缺少必要字段。")

    if not isinstance(parsed["entries"], list):
        raise ValueError("AI 返回的 entries 必须是列表。")

    _validate_balance(parsed["entries"])
    return parsed


def generate_report(db: Session, period: str) -> dict[str, Any]:
    """
    生成指定月份的财务分析报告。

    流程：
    1. 汇总指定月份的收入、支出和净利润
    2. 调用 DeepSeek 生成白话版中文分析
    3. 把结果存入 reports 表
    4. 返回报告数据
    """
    metrics = _summarize_period_metrics(db, period)

    system_prompt = (
        "你是专业会计助手。"
        "请基于提供的财务汇总数据，输出中文白话分析报告。"
        "报告要简明、专业、可读，适合管理者查看。"
    )

    user_prompt = f"""
请基于以下财务汇总数据，生成一段中文财务分析报告：

月份：{metrics['period']}
凭证数量：{metrics['voucher_count']}
总收入：{metrics['total_revenue']}
总支出：{metrics['total_expense']}
净利润：{metrics['net_profit']}

要求：
1. 用中文输出
2. 不要使用 Markdown 标题或代码块
3. 简明说明收入、支出、利润情况，并给出一句经营判断
""".strip()

    content = _call_deepseek(system_prompt, user_prompt)

    existing_report = db.scalar(select(Report).where(Report.period == period))
    if existing_report is None:
        report = Report(period=period, content=content)
        db.add(report)
    else:
        existing_report.content = content
        report = existing_report

    db.commit()
    db.refresh(report)

    return {
        "id": report.id,
        "period": report.period,
        "content": report.content,
        "created_at": report.created_at,
        "summary": metrics,
    }


def query_financial_data(db: Session, text: str) -> dict[str, str]:
    """
    根据自然语言查询财务数据，并由 AI 组织成中文回答。

    当前先聚焦于按月份汇总类问题，例如：
    - 上个月花了多少
    - 本月收入多少
    - 2026-03 净利润是多少
    """
    period = _infer_period_from_text(text)
    metrics = _summarize_period_metrics(db, period)

    system_prompt = (
        "你是专业会计助手。"
        "请根据提供的财务汇总数据，直接回答用户问题。"
        "回答必须为中文，简洁清楚，不要编造未提供的数据。"
    )

    user_prompt = f"""
用户问题：
{text}

可用财务数据：
月份：{metrics['period']}
凭证数量：{metrics['voucher_count']}
总收入：{metrics['total_revenue']}
总支出：{metrics['total_expense']}
净利润：{metrics['net_profit']}

请直接用中文回答用户问题。
""".strip()

    answer = _call_deepseek(system_prompt, user_prompt)
    return {"answer": answer, "period": period}
