"""
应收应付相关路由。

当前文件只提供接口骨架，
用于先完成接口注册与文档展示。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from core.auth import verify_token
from core.database import get_db
from models.receivable import ReceivableStatus, ReceivableType
from schemas.receivable import ReceivableCreate, ReceivableResponse
from services.accounting import receivable_service

# 创建应收应付路由。
# 所有接口统一要求管理员令牌。
router = APIRouter(
    prefix="/api/admin/receivables",
    tags=["Receivables"],
    dependencies=[Depends(verify_token)],
)


@router.get("/")
def list_receivables(
    type: ReceivableType | None = Query(default=None, description="类型筛选，可选"),
    status_param: ReceivableStatus | None = Query(
        default=None,
        alias="status",
        description="状态筛选，可选",
    ),
    db: Session = Depends(get_db),
) -> list[ReceivableResponse]:
    """
    获取应收应付列表。
    """
    return receivable_service.get_receivables(db, type, status_param)


@router.post("/")
def create_receivable(
    payload: ReceivableCreate,
    db: Session = Depends(get_db),
) -> ReceivableResponse:
    """
    新增一笔应收或应付记录。
    """
    return receivable_service.create_receivable(db, payload)


@router.patch("/{receivable_id}/settle")
def settle_receivable(
    receivable_id: int,
    db: Session = Depends(get_db),
) -> ReceivableResponse:
    """
    将指定应收应付记录标记为已结清。
    """
    try:
        return receivable_service.settle_receivable(db, receivable_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
