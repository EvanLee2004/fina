"""
会计科目相关路由。

当前文件只提供接口骨架，
用于先把接口注册到 /docs 并完成统一认证接入。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.auth import verify_token
from core.database import get_db
from schemas.account import AccountCreate, AccountResponse, AccountTree
from services import account_service

# 创建会计科目路由。
# 统一挂在 /api/admin/accounts 前缀下，并对所有接口应用管理员令牌校验。
router = APIRouter(
    prefix="/api/admin/accounts",
    tags=["Accounts"],
    dependencies=[Depends(verify_token)],
)


@router.get("/")
def list_accounts(db: Session = Depends(get_db)) -> list[AccountResponse]:
    """
    获取科目列表。

    只返回当前启用中的科目。
    """
    return account_service.get_accounts(db)


@router.get("/tree")
def get_account_tree(db: Session = Depends(get_db)) -> list[AccountTree]:
    """
    获取科目树结构。

    返回父子嵌套的树形数据结构。
    """
    return account_service.get_account_tree(db)


@router.post("/")
def create_account(
    payload: AccountCreate,
    db: Session = Depends(get_db),
) -> AccountResponse:
    """
    新增会计科目。

    如果科目编码重复或父科目不存在，
    则返回对应的 HTTP 错误。
    """
    try:
        return account_service.create_account(db, payload)
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


@router.patch("/{account_id}")
def update_account(
    account_id: int,
    payload: dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
) -> AccountResponse:
    """
    更新指定科目。

    当前先使用通用字典接收更新内容，
    后续如果字段收敛，再补专门的 Update Schema。
    """
    try:
        return account_service.update_account(db, account_id, payload)
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


@router.delete("/{account_id}")
def delete_account(
    account_id: int,
    db: Session = Depends(get_db),
) -> AccountResponse:
    """
    删除指定科目。

    当前采用软删除方式，
    实际上是把 is_active 改为 False。
    """
    try:
        return account_service.delete_account(db, account_id)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
