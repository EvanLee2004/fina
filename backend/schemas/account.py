"""
会计科目相关的 Pydantic Schema。

这个文件专门负责：
1. 定义创建科目时的请求结构。
2. 定义返回单个科目时的响应结构。
3. 定义返回科目树时的递归结构。
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from models.account import AccountType


class AccountCreate(BaseModel):
    """
    创建科目请求结构。

    用于接收前端或管理端提交的新科目数据。
    """

    # 科目编码。
    # 一般需要保持唯一，例如 1001、6001。
    code: str = Field(..., description="科目编码")

    # 科目名称。
    # 例如“库存现金”“主营业务收入”。
    name: str = Field(..., description="科目名称")

    # 科目类型。
    # 必须是系统约定的六大类之一。
    type: AccountType = Field(..., description="科目类型")

    # 父科目 ID。
    # 顶级科目可以不传，子科目则传入所属父级的 ID。
    parent_id: int | None = Field(default=None, description="父科目 ID，可选")


class AccountResponse(BaseModel):
    """
    单个科目响应结构。

    用于返回普通科目详情或列表项数据。
    """

    model_config = ConfigDict(from_attributes=True)

    # 科目主键 ID。
    id: int = Field(..., description="科目主键 ID")

    # 科目编码。
    code: str = Field(..., description="科目编码")

    # 科目名称。
    name: str = Field(..., description="科目名称")

    # 科目类型。
    type: AccountType = Field(..., description="科目类型")

    # 父科目 ID。
    parent_id: int | None = Field(default=None, description="父科目 ID")

    # 是否启用。
    is_active: bool = Field(..., description="是否启用")

    # 创建时间。
    created_at: datetime = Field(..., description="创建时间")


class AccountTree(BaseModel):
    """
    科目树响应结构。

    在普通科目字段基础上增加 children，
    用于返回多级树形科目数据。
    """

    model_config = ConfigDict(from_attributes=True)

    # 科目主键 ID。
    id: int = Field(..., description="科目主键 ID")

    # 科目编码。
    code: str = Field(..., description="科目编码")

    # 科目名称。
    name: str = Field(..., description="科目名称")

    # 科目类型。
    type: AccountType = Field(..., description="科目类型")

    # 父科目 ID。
    parent_id: int | None = Field(default=None, description="父科目 ID")

    # 是否启用。
    is_active: bool = Field(..., description="是否启用")

    # 创建时间。
    created_at: datetime = Field(..., description="创建时间")

    # 子科目列表。
    # 使用默认空列表，方便直接返回树形结构。
    children: list["AccountTree"] = Field(default_factory=list, description="子科目列表")


AccountTree.model_rebuild()
