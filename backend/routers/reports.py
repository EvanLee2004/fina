"""
财务报告相关路由。

当前文件只提供接口骨架，
用于先完成接口注册与文档展示。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.auth import verify_token
from core.database import get_db
from schemas.report import ReportResponse
from services import report_service

# 创建财务报告路由。
# 所有接口统一要求管理员令牌。
router = APIRouter(
    prefix="/api/admin/reports",
    tags=["Reports"],
    dependencies=[Depends(verify_token)],
)


@router.get("/")
def list_reports(db: Session = Depends(get_db)) -> list[ReportResponse]:
    """
    获取报告列表。
    """
    return report_service.get_reports(db)


@router.get("/{period}")
def get_report_by_period(
    period: str,
    db: Session = Depends(get_db),
) -> ReportResponse:
    """
    获取指定月份的财务报告。
    """
    try:
        return report_service.get_report_by_period(db, period)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
