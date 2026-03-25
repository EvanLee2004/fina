"""
统一对话接口的请求/响应结构。
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """对话请求。"""

    # 会话 ID，用于多轮对话续接。不传则自动生成新会话。
    session_id: str | None = Field(None, description="会话 ID，不传则新建会话")

    # 用户消息。
    message: str = Field(..., min_length=1, description="用户消息内容")

    # 可选模型名；不传时，统一使用后端默认模型。
    model: str | None = Field(None, description="本轮对话使用的模型名")


class ActionRecord(BaseModel):
    """AI 执行的单个操作记录。"""
    type: str = Field(..., description="操作类型，例如 voucher_created, memory_updated")
    detail: dict | None = Field(None, description="操作详情")


class ChatResponse(BaseModel):
    """对话响应。"""

    # AI 的回复文本。
    reply: str = Field(..., description="AI 回复")

    # 当前会话 ID，方便调用方续接对话。
    session_id: str = Field(..., description="会话 ID")

    # AI 执行的操作列表。
    actions: list[ActionRecord] = Field(default_factory=list, description="执行的操作")

    # 本次回复用到的记忆。
    memories_used: list[str] = Field(default_factory=list, description="使用的记忆摘要")
