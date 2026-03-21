"""
凭证相关路由。

当前文件只提供接口骨架，
用于先完成接口注册和文档展示。
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query

from core.auth import verify_token
from schemas.voucher import VoucherCreate

# 创建凭证路由。
# 所有接口统一走管理员令牌校验。
router = APIRouter(
    prefix="/api/admin/vouchers",
    tags=["Vouchers"],
    dependencies=[Depends(verify_token)],
)


@router.get("/")
def list_vouchers(
    start_date: date | None = Query(default=None, description="开始日期，可选"),
    end_date: date | None = Query(default=None, description="结束日期，可选"),
) -> dict[str, str]:
    """
    获取凭证列表，并支持按日期范围筛选。
    """
    _ = (start_date, end_date)
    return {"message": "ok"}


@router.get("/{voucher_id}")
def get_voucher(voucher_id: int) -> dict[str, str]:
    """
    获取单条凭证详情。
    """
    _ = voucher_id
    return {"message": "ok"}


@router.post("/")
def create_voucher(payload: VoucherCreate) -> dict[str, str]:
    """
    新增凭证。
    """
    _ = payload
    return {"message": "ok"}


@router.patch("/{voucher_id}/approve")
def approve_voucher(voucher_id: int) -> dict[str, str]:
    """
    审核指定凭证。
    """
    _ = voucher_id
    return {"message": "ok"}


@router.delete("/{voucher_id}")
def delete_voucher(voucher_id: int) -> dict[str, str]:
    """
    删除指定凭证。
    """
    _ = voucher_id
    return {"message": "ok"}
