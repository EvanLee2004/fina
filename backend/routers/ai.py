"""
AI 能力相关路由。

当前文件只提供接口骨架，
用于先将 AI 接口注册到文档中。
"""

from __future__ import annotations

import httpx

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.auth import verify_token
from core.database import get_db
from schemas.ai import NLInput, QueryInput, ReportRequest
from services import ai_service

# 创建 AI 路由。
# 所有接口统一要求管理员令牌。
router = APIRouter(
    prefix="/api/admin/ai",
    tags=["AI"],
    dependencies=[Depends(verify_token)],
)


@router.post("/parse")
def parse_natural_language(
    payload: NLInput,
    db: Session = Depends(get_db),
) -> dict:
    """
    将自然语言描述解析为凭证草稿。
    """
    try:
        return ai_service.parse_natural_language(db, payload.text)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"调用 DeepSeek API 失败：{exc}",
        ) from exc


@router.post("/report")
def generate_report(
    payload: ReportRequest,
    db: Session = Depends(get_db),
) -> dict:
    """
    生成财务分析报告。
    """
    try:
        return ai_service.generate_report(db, payload.period)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"调用 DeepSeek API 失败：{exc}",
        ) from exc


@router.post("/query")
def query_financial_data(
    payload: QueryInput,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """
    根据自然语言查询财务数据。
    """
    try:
        return ai_service.query_financial_data(db, payload.text)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"调用 DeepSeek API 失败：{exc}",
        ) from exc
