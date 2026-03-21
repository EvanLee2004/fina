"""
会计科目相关路由。

当前文件只提供接口骨架，
用于先把接口注册到 /docs 并完成统一认证接入。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends

from core.auth import verify_token
from schemas.account import AccountCreate

# 创建会计科目路由。
# 统一挂在 /api/admin/accounts 前缀下，并对所有接口应用管理员令牌校验。
router = APIRouter(
    prefix="/api/admin/accounts",
    tags=["Accounts"],
    dependencies=[Depends(verify_token)],
)


@router.get("/")
def list_accounts() -> dict[str, str]:
    """
    获取科目列表。

    当前先返回占位响应，
    后续再接入真实的数据库查询逻辑。
    """
    return {"message": "ok"}


@router.get("/tree")
def get_account_tree() -> dict[str, str]:
    """
    获取科目树结构。

    当前先返回占位响应，
    后续再补充树形组装逻辑。
    """
    return {"message": "ok"}


@router.post("/")
def create_account(payload: AccountCreate) -> dict[str, str]:
    """
    新增会计科目。

    参数使用 AccountCreate，
    方便 /docs 展示请求体结构。
    """
    _ = payload
    return {"message": "ok"}


@router.patch("/{account_id}")
def update_account(account_id: int, payload: dict[str, Any] = Body(...)) -> dict[str, str]:
    """
    更新指定科目。

    当前先使用通用字典接收更新内容，
    后续再根据实际更新策略补充专门的 Update Schema。
    """
    _ = (account_id, payload)
    return {"message": "ok"}


@router.delete("/{account_id}")
def delete_account(account_id: int) -> dict[str, str]:
    """
    删除指定科目。

    当前只返回占位响应。
    """
    _ = account_id
    return {"message": "ok"}
