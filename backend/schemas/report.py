"""
财务报告相关的 Pydantic Schema。

这个文件专门负责定义报告返回结构。
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ReportResponse(BaseModel):
    """
    财务报告响应结构。

    用于返回单条已生成的 AI 财务报告数据。
    """

    model_config = ConfigDict(from_attributes=True)

    # 报告主键 ID。
    id: int = Field(..., description="报告主键 ID")

    # 报告月份。
    period: str = Field(..., description="报告月份，格式 2024-03")

    # AI 生成的报告正文。
    content: str = Field(..., description="AI 生成的报告文字")

    # 创建时间。
    created_at: datetime = Field(..., description="创建时间")
