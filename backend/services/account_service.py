"""
会计科目服务层。

这个文件专门负责：
1. 查询启用中的科目列表。
2. 组装树形科目结构。
3. 新增、更新、软删除科目。
4. 处理科目编码重复、科目不存在等核心业务校验。
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.account import Account


def get_accounts(db: Session) -> list[Account]:
    """
    查询所有启用中的科目列表。

    只返回 is_active=True 的科目，
    并按科目编码升序排列，便于页面展示和查找。
    """
    statement = (
        select(Account)
        .where(Account.is_active.is_(True))
        .order_by(Account.code.asc())
    )
    return list(db.scalars(statement).all())


def get_account_tree(db: Session) -> list[dict[str, Any]]:
    """
    查询启用中的科目树结构。

    返回值使用字典嵌套 children 列表的形式，
    方便直接交给 Pydantic 的 AccountTree 响应结构进行序列化。
    """
    accounts = get_accounts(db)

    # 先把所有科目平铺转换为可嵌套的字典节点。
    # 这样后续可以通过 parent_id 快速组装树形关系。
    nodes: dict[int, dict[str, Any]] = {
        account.id: {
            "id": account.id,
            "code": account.code,
            "name": account.name,
            "type": account.type,
            "parent_id": account.parent_id,
            "is_active": account.is_active,
            "created_at": account.created_at,
            "children": [],
        }
        for account in accounts
    }

    roots: list[dict[str, Any]] = []

    # 根据 parent_id 将每个节点挂到对应父节点下面。
    for account in accounts:
        node = nodes[account.id]

        # 顶级科目直接放进根节点列表。
        if account.parent_id is None:
            roots.append(node)
            continue

        parent_node = nodes.get(account.parent_id)

        # 如果父节点不存在，说明数据存在悬挂关系。
        # 当前容错处理为把该节点当作根节点返回，避免整棵树构建失败。
        if parent_node is None:
            roots.append(node)
            continue

        parent_node["children"].append(node)

    return roots


def create_account(db: Session, data: Any) -> Account:
    """
    新增科目。

    核心校验：
    - 科目编码不能重复
    - 如果指定了父科目，则父科目必须存在且处于启用状态
    """
    existing_account = db.scalar(
        select(Account).where(Account.code == data.code)
    )
    if existing_account is not None:
        raise ValueError("科目编码已存在。")

    if data.parent_id is not None:
        parent_account = db.get(Account, data.parent_id)
        if parent_account is None or not parent_account.is_active:
            raise LookupError("父科目不存在。")

    account = Account(
        code=data.code,
        name=data.name,
        type=data.type,
        parent_id=data.parent_id,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


def update_account(db: Session, account_id: int, data: dict[str, Any]) -> Account:
    """
    更新指定科目。

    核心校验：
    - 找不到科目时抛出 LookupError
    - 更新 code 时不能与其他科目重复
    - 更新 parent_id 时，父科目必须存在
    """
    account = db.get(Account, account_id)
    if account is None:
        raise LookupError("科目不存在。")

    allowed_fields = {"code", "name", "type", "parent_id", "is_active"}
    update_data = {key: value for key, value in data.items() if key in allowed_fields}

    # 如果本次请求没有可更新字段，则直接返回当前数据。
    if not update_data:
        return account

    new_code = update_data.get("code")
    if new_code and new_code != account.code:
        existing_account = db.scalar(
            select(Account).where(Account.code == new_code, Account.id != account_id)
        )
        if existing_account is not None:
            raise ValueError("科目编码已存在。")

    if "parent_id" in update_data:
        parent_id = update_data["parent_id"]

        # 禁止把自己设置成自己的父节点，避免出现循环引用。
        if parent_id == account_id:
            raise ValueError("父科目不能是自己。")

        if parent_id is not None:
            parent_account = db.get(Account, parent_id)
            if parent_account is None or not parent_account.is_active:
                raise LookupError("父科目不存在。")

    for key, value in update_data.items():
        setattr(account, key, value)

    db.commit()
    db.refresh(account)
    return account


def delete_account(db: Session, account_id: int) -> Account:
    """
    软删除指定科目。

    实际删除方式是把 is_active 改成 False，
    以保留历史数据并避免直接物理删除带来的审计问题。
    """
    account = db.get(Account, account_id)
    if account is None:
        raise LookupError("科目不存在。")

    account.is_active = False
    db.commit()
    db.refresh(account)
    return account
