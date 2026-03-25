"""
财务报告相关的 Pydantic Schema。

这个文件不再只返回一段纯文本，
而是统一承载：
1. 客观财务汇总数据
2. AI 财务分析
3. 风险提示
4. 行动建议
"""

from __future__ import annotations

from datetime import datetime

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class MetricCard(BaseModel):
    """
    报告顶部的关键指标卡片。

    这部分全部由代码计算，确保口径稳定、可追溯。
    """

    label: str = Field(..., description="指标名称")
    value: Decimal = Field(..., description="指标值")
    unit: str = Field(default="CNY", description="指标单位")


class ExpenseBreakdownItem(BaseModel):
    """
    费用结构项。

    用于展示期间内主要费用/成本科目的金额分布。
    """

    account_name: str = Field(..., description="科目名称")
    amount: Decimal = Field(..., description="金额")


class AgingBucket(BaseModel):
    """
    应收应付账龄分桶结果。
    """

    label: str = Field(..., description="账龄区间标签")
    amount: Decimal = Field(..., description="金额")


class FinancialObjectiveSummary(BaseModel):
    """
    客观财务汇总。

    这里面的每个字段都来自后端代码统计，而不是模型自由生成。
    """

    voucher_count: int = Field(..., description="凭证数量")
    total_revenue: Decimal = Field(..., description="收入总额")
    total_expense: Decimal = Field(..., description="支出总额")
    net_profit: Decimal = Field(..., description="净利润")
    pending_receivables: Decimal = Field(..., description="待收款总额")
    pending_payables: Decimal = Field(..., description="待付款总额")
    expense_breakdown: list[ExpenseBreakdownItem] = Field(
        default_factory=list,
        description="主要费用结构",
    )
    receivable_aging: list[AgingBucket] = Field(
        default_factory=list,
        description="应收账龄分布",
    )
    payable_aging: list[AgingBucket] = Field(
        default_factory=list,
        description="应付账龄分布",
    )


class FinancialNarrative(BaseModel):
    """
    AI 财务分析正文。

    这一层由模型根据客观数据和长期记忆生成。
    """

    executive_summary: str = Field(..., description="财务概览摘要")
    analysis: str = Field(..., description="财务视角分析")
    risks: list[str] = Field(default_factory=list, description="风险与异常")
    recommendations: list[str] = Field(default_factory=list, description="建议动作")


class FinancialReportResponse(BaseModel):
    """
    面向接口调用方的完整财务报告响应。
    """

    period: str = Field(..., description="报告期间，格式 YYYY-MM")
    metrics: list[MetricCard] = Field(default_factory=list, description="关键指标卡片")
    objective_summary: FinancialObjectiveSummary = Field(..., description="客观财务汇总")
    narrative: FinancialNarrative = Field(..., description="AI 财务分析")
    content: str = Field(..., description="整合后的可直接展示文本")


class StoredReportResponse(BaseModel):
    """
    已存档报告响应结构。

    用于列表或简单查询场景，保留归档能力。
    """

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="报告主键 ID")
    period: str = Field(..., description="报告月份，格式 2024-03")
    content: str = Field(..., description="AI 生成的报告文字")
    objective_json: str | None = Field(default=None, description="客观财务数据快照 JSON")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
