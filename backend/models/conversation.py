"""
对话会话和消息模型定义。

支持多轮对话，按 session 管理上下文。

这里的数据存放在独立记忆库中，而不是财务主库。
这样可以把“业务账数据”和“AI 记忆/对话数据”彻底拆开。
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.memory_database import MemoryBase


class MessageRole(str, Enum):
    """消息角色枚举。"""
    USER = "user"
    ASSISTANT = "assistant"


class Conversation(MemoryBase):
    """对话会话 ORM 模型。"""

    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True,
    )

    # 会话标识，由调用方提供，用于多轮对话续接。
    session_id: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True, index=True,
        comment="会话标识",
    )

    # 会话摘要，AI 自动生成的对话主题概述。
    summary: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="会话摘要",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    messages: Mapped[list["Message"]] = relationship(
        "Message", back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )


class Message(MemoryBase):
    """对话消息 ORM 模型。"""

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True,
    )

    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    role: Mapped[MessageRole] = mapped_column(
        SqlEnum(MessageRole, name="message_role"),
        nullable=False,
    )

    content: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="消息内容",
    )

    # 存储 AI 执行的操作记录，JSON 格式。
    actions_json: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="AI 执行的操作记录（JSON）",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    conversation: Mapped["Conversation"] = relationship(
        "Conversation", back_populates="messages",
    )
