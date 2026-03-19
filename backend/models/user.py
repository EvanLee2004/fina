"""
用户表模型定义。

这个文件的职责是：
1. 定义系统用户表 users。
2. 约束用户角色，只允许 common / boss / accountant 三种值。
3. 为后续登录、权限控制、用户管理提供 ORM 模型。
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Boolean, DateTime, Enum as SqlEnum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class UserRole(str, Enum):
    """
    用户角色枚举。

    这里使用 Python 枚举来约束 role 字段的可选值，
    避免业务代码里到处散落硬编码字符串。

    当前权限约定：
    - common: 只有查看权限，不能修改业务数据
    - boss: 可以查看和修改业务数据
    - accountant: 可以查看和修改业务数据
    """

    # 普通查看角色。
    # 该角色只有只读权限，不能新增、修改或删除业务数据。
    COMMON = "common"

    # 老板角色，通常拥有系统最高权限。
    # 在当前项目约定中，老板可以执行数据库写操作。
    BOSS = "boss"

    # 会计角色，通常负责记账、审核、报表等业务操作。
    # 在当前项目约定中，会计也可以执行数据库写操作。
    ACCOUNTANT = "accountant"


class User(Base):
    """
    用户 ORM 模型。

    这个模型会映射到 PostgreSQL 中的 users 表。
    后续登录认证、JWT 签发、用户查询等功能都会依赖这个表。
    """

    # 指定数据库中的表名。
    __tablename__ = "users"

    # 用户主键 ID。
    # 使用自增整数作为主键，便于在系统内部做关联和查询。
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="用户主键 ID",
    )

    # 用户登录名。
    # 设置 unique=True，保证用户名在系统内唯一，避免重复注册。
    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="用户名，用于登录和唯一标识用户",
    )

    # 用户加密后的密码。
    # 这里明确保存的是哈希值，不保存明文密码。
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="用户密码的哈希值，不能保存明文密码",
    )

    # 用户角色。
    # 使用数据库枚举字段与 Python 枚举绑定。
    # 当前允许 common / boss / accountant 三种角色值。
    role: Mapped[UserRole] = mapped_column(
        SqlEnum(UserRole, name="user_role"),
        nullable=False,
        default=UserRole.COMMON,
        comment="用户角色，限定为 common、boss 或 accountant",
    )

    # 用户是否启用。
    # 当账号被禁用时，可以通过这个字段阻止其继续登录或访问系统。
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="账号是否启用，False 表示禁用",
    )

    # 用户创建时间。
    # 默认使用当前 UTC 时间，记录该账号最初创建的时刻。
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="用户创建时间",
    )
