"""
凭证相关路由。

当前文件只提供接口骨架，
用于先完成接口注册和文档展示。
"""

from __future__ import annotations

from datetime import date as DateType

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from core.auth import verify_token
from core.database import get_db
from schemas.voucher import VoucherCreate, VoucherResponse
from services.accounting import voucher_service

# 创建凭证路由。
# 所有接口统一走管理员令牌校验。
router = APIRouter(
    prefix="/api/admin/vouchers",
    tags=["Vouchers"],
    dependencies=[Depends(verify_token)],
)


@router.get("/")
def list_vouchers(
    start_date: DateType | None = Query(default=None, description="开始日期，可选"),
    end_date: DateType | None = Query(default=None, description="结束日期，可选"),
    db: Session = Depends(get_db),
) -> list[VoucherResponse]:
    """
    获取凭证列表，并支持按日期范围筛选。
    """
    return voucher_service.get_vouchers(db, start_date, end_date)


@router.get("/{voucher_id}")
def get_voucher(
    voucher_id: int,
    db: Session = Depends(get_db),
) -> VoucherResponse:
    """
    获取单条凭证详情。
    """
    try:
        return voucher_service.get_voucher(db, voucher_id)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post("/")
def create_voucher(
    payload: VoucherCreate,
    db: Session = Depends(get_db),
) -> VoucherResponse:
    """
    新增凭证。
    """
    try:
        return voucher_service.create_voucher(db, payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.patch("/{voucher_id}/approve")
def approve_voucher(
    voucher_id: int,
    db: Session = Depends(get_db),
) -> VoucherResponse:
    """
    审核指定凭证。
    """
    try:
        return voucher_service.approve_voucher(db, voucher_id)
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


@router.delete("/{voucher_id}")
def delete_voucher(
    voucher_id: int,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """
    删除指定凭证。
    """
    try:
        voucher_service.delete_voucher(db, voucher_id)
        return {"message": "ok"}
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
