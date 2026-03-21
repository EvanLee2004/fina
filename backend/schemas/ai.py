"""
AI 能力相关的 Pydantic Schema。

这个文件专门负责：
1. 定义自然语言输入结构。
2. 定义 AI 解析出的凭证草稿结构。
3. 定义自然语言查询结构。
4. 定义报告生成请求结构。
"""

from __future__ import annotations

from datetime import date as DateType
from decimal import Decimal

from pydantic import BaseModel, Field


class NLInput(BaseModel):
    """
    自然语言记账输入结构。

    用于接收用户输入的一段自然语言业务描述。
    """

    # 用户输入的自然语言文本。
    text: str = Field(..., description="用户输入的自然语言文本")


class VoucherDraftEntry(BaseModel):
    """
    AI 解析出的凭证草稿分录结构。

    用于表示 AI 从自然语言中提取出的单条分录结果。
    """

    # 会计科目 ID。
    account_id: int = Field(..., description="会计科目 ID")

    # 借方金额。
    debit: Decimal = Field(..., description="借方金额")

    # 贷方金额。
    credit: Decimal = Field(..., description="贷方金额")


class VoucherDraft(BaseModel):
    """
    AI 解析出的凭证草稿结构。

    用于返回 AI 推断的凭证日期、摘要和分录列表。
    """

    # 凭证日期。
    date: DateType = Field(..., description="凭证日期")

    # 凭证摘要。
    memo: str = Field(..., description="凭证摘要")

    # AI 解析出的分录列表。
    entries: list[VoucherDraftEntry] = Field(default_factory=list, description="分录列表")


class QueryInput(BaseModel):
    """
    自然语言查询输入结构。

    用于接收用户关于财务数据的自然语言查询。
    """

    # 用户查询文本。
    text: str = Field(..., description="用户查询的自然语言文本")


class ReportRequest(BaseModel):
    """
    财务报告生成请求结构。

    用于指定要生成哪一个月份的报告。
    """

    # 报告月份。
    # 按你的要求使用 YYYY-MM 格式，例如 2024-03。
    period: str = Field(..., pattern=r"^\d{4}-\d{2}$", description="报告月份，格式 2024-03")
