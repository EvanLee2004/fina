"""
应收应付相关路由。

当前文件只提供接口骨架，
用于先完成接口注册与文档展示。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from core.auth import verify_token
from schemas.receivable import ReceivableCreate

# 创建应收应付路由。
# 所有接口统一要求管理员令牌。
router = APIRouter(
    prefix="/api/admin/receivables",
    tags=["Receivables"],
    dependencies=[Depends(verify_token)],
)


@router.get("/")
def list_receivables() -> dict[str, str]:
    """
    获取应收应付列表。
    """
    return {"message": "ok"}


@router.post("/")
def create_receivable(payload: ReceivableCreate) -> dict[str, str]:
    """
    新增一笔应收或应付记录。
    """
    _ = payload
    return {"message": "ok"}


@router.patch("/{receivable_id}/settle")
def settle_receivable(receivable_id: int) -> dict[str, str]:
    """
    将指定应收应付记录标记为已结清。
    """
    _ = receivable_id
    return {"message": "ok"}
