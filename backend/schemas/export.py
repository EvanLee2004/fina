"""
导出能力相关的 Pydantic Schema。

这里统一描述 Excel 与 Word 两类交付物，
方便后续通过工具调用或 HTTP 接口复用同一套结构。
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ExportRequest(BaseModel):
    """
    导出请求结构。

    当前以月份为核心参数，后续如需支持季度/年度导出，
    可以继续在这里扩展。
    """

    period: str = Field(..., pattern=r"^\d{4}-\d{2}$", description="导出期间，格式 YYYY-MM")
    model: str | None = Field(
        None,
        description="可选模型名，只影响导出中由 AI 生成的分析内容",
    )


class ExportFileResponse(BaseModel):
    """
    单个导出文件响应结构。
    """

    file_type: str = Field(..., description="导出文件类型，例如 xlsx 或 docx")
    period: str = Field(..., description="导出期间")
    filename: str = Field(..., description="导出文件名")
    path: str = Field(..., description="导出文件绝对路径")


class CombinedExportResponse(BaseModel):
    """
    同时导出多个文件时的统一返回结构。
    """

    period: str = Field(..., description="导出期间")
    files: list[ExportFileResponse] = Field(default_factory=list, description="导出结果列表")
