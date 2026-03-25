"""
公司会计政策相关 Schema。

这些结构负责让前端或外部系统显式配置公司会计口径，
避免 AI 在没有边界条件的情况下自由发挥。
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from models.accounting_policy import AccountingStandard, TaxpayerType


class AccountingPolicyUpdate(BaseModel):
    """
    会计政策更新请求。

    这里采用“部分更新”风格，
    方便你逐步补齐公司政策，而不是一次填完所有字段。
    """

    company_name: str | None = Field(None, description="公司名称")
    accounting_standard: AccountingStandard | None = Field(
        None,
        description="会计准则：small_business 或 enterprise",
    )
    taxpayer_type: TaxpayerType | None = Field(
        None,
        description="纳税人类型：small_scale 或 general",
    )
    currency: str | None = Field(None, description="记账币种，默认 CNY")
    standard_locked: bool | None = Field(
        None,
        description="是否锁定会计准则，锁定后不能随意切换",
    )
    require_manual_confirmation: bool | None = Field(
        None,
        description="AI 记账草稿是否必须人工确认",
    )
    notes: str | None = Field(None, description="补充政策说明")
    stripe_receipt_debit_account_id: int | None = Field(
        None,
        description="Stripe 收款默认借方科目 ID",
    )
    stripe_receipt_credit_account_id: int | None = Field(
        None,
        description="Stripe 收款默认贷方科目 ID",
    )


class AccountingPolicyResponse(BaseModel):
    """
    会计政策响应结构。
    """

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="会计政策主键 ID")
    company_name: str | None = Field(None, description="公司名称")
    accounting_standard: AccountingStandard | None = Field(
        None,
        description="会计准则",
    )
    taxpayer_type: TaxpayerType | None = Field(None, description="纳税人类型")
    currency: str = Field(..., description="记账币种")
    standard_locked: bool = Field(..., description="是否锁定会计准则")
    require_manual_confirmation: bool = Field(..., description="是否必须人工确认")
    notes: str | None = Field(None, description="补充政策说明")
    stripe_receipt_debit_account_id: int | None = Field(
        None,
        description="Stripe 收款默认借方科目 ID",
    )
    stripe_receipt_credit_account_id: int | None = Field(
        None,
        description="Stripe 收款默认贷方科目 ID",
    )
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
