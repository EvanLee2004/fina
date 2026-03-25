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
from core.memory_database import get_memory_db
from schemas.ai import NLInput, QueryInput, ReportRequest
from schemas.report import FinancialReportResponse
from services.integrations import llm_service
from services.reporting import report_service

# 创建 AI 路由。
# 所有接口统一要求管理员令牌。
router = APIRouter(
    prefix="/api/admin/ai",
    tags=["AI"],
    dependencies=[Depends(verify_token)],
)


@router.get("/models")
def list_available_models() -> dict:
    """
    返回当前后端可调用的模型信息。
    """
    return llm_service.get_ai_model_catalog()


@router.post("/parse")
def parse_natural_language(
    payload: NLInput,
    db: Session = Depends(get_db),
) -> dict:
    """
    将自然语言描述解析为凭证草稿。
    """
    try:
        return llm_service.parse_natural_language(db, payload.text, model=payload.model)
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
    memory_db: Session = Depends(get_memory_db),
) -> FinancialReportResponse:
    """
    生成财务分析报告。
    """
    try:
        return report_service.generate_financial_report(
            db,
            memory_db,
            payload.period,
            model=payload.model,
        )
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
    memory_db: Session = Depends(get_memory_db),
) -> dict[str, str]:
    """
    根据自然语言查询财务数据。
    """
    try:
        from services.agent.chat_service import _infer_period_from_text

        period = _infer_period_from_text(payload.text)
        report = report_service.generate_financial_report(
            db,
            memory_db,
            period,
            model=payload.model,
        )
        return {"answer": report.content, "period": period}
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
