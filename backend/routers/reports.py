"""
财务报告相关路由。

当前文件只提供接口骨架，
用于先完成接口注册与文档展示。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from core.auth import verify_token

# 创建财务报告路由。
# 所有接口统一要求管理员令牌。
router = APIRouter(
    prefix="/api/admin/reports",
    tags=["Reports"],
    dependencies=[Depends(verify_token)],
)


@router.get("/")
def list_reports() -> dict[str, str]:
    """
    获取报告列表。
    """
    return {"message": "ok"}


@router.get("/{period}")
def get_report_by_period(period: str) -> dict[str, str]:
    """
    获取指定月份的财务报告。
    """
    _ = period
    return {"message": "ok"}
