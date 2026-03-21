"""
凭证相关的 Pydantic Schema。

这个文件专门负责：
1. 定义凭证分录创建请求结构。
2. 定义凭证创建请求结构。
3. 定义凭证响应结构。
"""

from __future__ import annotations

from datetime import date as DateType, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from models.voucher import VoucherStatus


class VoucherEntryCreate(BaseModel):
    """
    凭证分录创建请求结构。

    用于接收单条借贷分录数据。
    """

    # 会计科目 ID。
    account_id: int = Field(..., description="会计科目 ID")

    # 借方金额。
    debit: Decimal = Field(..., description="借方金额")

    # 贷方金额。
    credit: Decimal = Field(..., description="贷方金额")


class VoucherCreate(BaseModel):
    """
    凭证创建请求结构。

    用于接收一张完整凭证及其分录列表。
    """

    # 凭证日期。
    date: DateType = Field(..., description="凭证日期")

    # 摘要。
    memo: str = Field(..., description="凭证摘要")

    # 分录列表。
    # 一张凭证通常由两条或多条分录组成。
    entries: list[VoucherEntryCreate] = Field(..., description="凭证分录列表")


class VoucherEntryResponse(BaseModel):
    """
    凭证分录响应结构。

    用于在返回凭证详情时携带分录信息。
    """

    model_config = ConfigDict(from_attributes=True)

    # 分录主键 ID。
    id: int = Field(..., description="分录主键 ID")

    # 所属凭证 ID。
    voucher_id: int = Field(..., description="所属凭证 ID")

    # 会计科目 ID。
    account_id: int = Field(..., description="会计科目 ID")

    # 借方金额。
    debit: Decimal = Field(..., description="借方金额")

    # 贷方金额。
    credit: Decimal = Field(..., description="贷方金额")


class VoucherResponse(BaseModel):
    """
    凭证响应结构。

    返回凭证主信息及对应的分录列表。
    """

    model_config = ConfigDict(from_attributes=True)

    # 凭证主键 ID。
    id: int = Field(..., description="凭证主键 ID")

    # 凭证日期。
    date: DateType = Field(..., description="凭证日期")

    # 摘要。
    memo: str = Field(..., description="凭证摘要")

    # 凭证状态。
    status: VoucherStatus = Field(..., description="凭证状态")

    # 创建人标识。
    created_by: int = Field(..., description="创建人标识")

    # 创建时间。
    created_at: datetime = Field(..., description="创建时间")

    # 分录列表。
    entries: list[VoucherEntryResponse] = Field(default_factory=list, description="分录列表")
