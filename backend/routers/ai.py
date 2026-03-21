"""
AI 能力相关路由。

当前文件只提供接口骨架，
用于先将 AI 接口注册到文档中。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from core.auth import verify_token
from schemas.ai import NLInput, QueryInput, ReportRequest

# 创建 AI 路由。
# 所有接口统一要求管理员令牌。
router = APIRouter(
    prefix="/api/admin/ai",
    tags=["AI"],
    dependencies=[Depends(verify_token)],
)


@router.post("/parse")
def parse_natural_language(payload: NLInput) -> dict[str, str]:
    """
    将自然语言描述解析为凭证草稿。
    """
    _ = payload
    return {"message": "ok"}


@router.post("/report")
def generate_report(payload: ReportRequest) -> dict[str, str]:
    """
    生成财务分析报告。
    """
    _ = payload
    return {"message": "ok"}


@router.post("/query")
def query_financial_data(payload: QueryInput) -> dict[str, str]:
    """
    根据自然语言查询财务数据。
    """
    _ = payload
    return {"message": "ok"}
