"""
应收应付相关的 Pydantic Schema。

这个文件专门负责：
1. 定义应收应付创建请求结构。
2. 定义应收应付响应结构。
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from models.receivable import ReceivableStatus, ReceivableType


class ReceivableCreate(BaseModel):
    """
    应收应付创建请求结构。

    用于接收一笔应收或应付记录的创建数据。
    """

    # 往来款项类型。
    type: ReceivableType = Field(..., description="往来款项类型")

    # 往来单位名称。
    party: str = Field(..., description="往来单位名称")

    # 往来金额。
    amount: Decimal = Field(..., description="往来金额")

    # 到期日。
    due_date: date | None = Field(default=None, description="到期日，可为空")

    # 备注。
    memo: str | None = Field(default=None, description="备注信息，可为空")


class ReceivableResponse(BaseModel):
    """
    应收应付响应结构。

    用于返回完整的应收应付记录详情。
    """

    model_config = ConfigDict(from_attributes=True)

    # 主键 ID。
    id: int = Field(..., description="应收应付主键 ID")

    # 往来款项类型。
    type: ReceivableType = Field(..., description="往来款项类型")

    # 往来单位名称。
    party: str = Field(..., description="往来单位名称")

    # 往来金额。
    amount: Decimal = Field(..., description="往来金额")

    # 到期日。
    due_date: date | None = Field(default=None, description="到期日")

    # 当前状态。
    status: ReceivableStatus = Field(..., description="款项状态")

    # 备注。
    memo: str | None = Field(default=None, description="备注信息")

    # 创建时间。
    created_at: datetime = Field(..., description="创建时间")
