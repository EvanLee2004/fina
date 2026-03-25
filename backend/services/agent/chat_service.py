"""
统一对话编排服务。

这是整个财务数字员工的核心调度器：
1. 管理会话
2. 加载公司画像和长期记忆
3. 加载最近对话历史
4. 识别意图
5. 调用对应处理器
6. 保存对话消息
7. 对本轮对话做长期记忆蒸馏
8. 返回结构化响应
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.conversation import Conversation, Message, MessageRole
from services.agent.brain_service import handle_chat, handle_query, handle_record, handle_report
from services.agent.intent_service import Intent, classify_intent, extract_keywords
from services.agent.memory_service import (
    distill_long_term_memories,
    format_memories_for_prompt,
    format_recent_messages_for_prompt,
    get_profile_memories,
    search_long_term_memories,
)
from services.reporting.report_service import generate_financial_report


def chat(
    db: Session,
    memory_db: Session,
    session_id: str | None,
    message: str,
    model: str | None = None,
) -> dict:
    """
    统一对话入口。

    当前采用单公司模式，对话只需要 session_id 即可维持上下文。
    """
    if not session_id:
        session_id = f"s_{uuid.uuid4().hex[:12]}"

    conversation = _get_or_create_conversation(memory_db, session_id)

    # 先取最近历史，再把本轮用户消息拼进去，给模型更完整的上下文。
    recent_messages = _get_recent_messages(memory_db, conversation.id, limit=10)
    preview_messages = [
        *recent_messages,
        Message(role=MessageRole.USER, content=message, conversation_id=conversation.id),
    ]

    profile_memories = get_profile_memories(memory_db)
    keywords = extract_keywords(message)
    long_term_memories = search_long_term_memories(memory_db, keywords)

    profile_memories_text = format_memories_for_prompt(profile_memories)
    long_term_memories_text = format_memories_for_prompt(long_term_memories)
    conversation_context_text = format_recent_messages_for_prompt(preview_messages)

    intent = classify_intent(message)

    if intent == Intent.RECORD:
        result = handle_record(
            db=db,
            text=message,
            profile_memories_text=profile_memories_text,
            long_term_memories_text=long_term_memories_text,
            conversation_context_text=conversation_context_text,
            model=model,
        )
    elif intent == Intent.QUERY:
        period = _infer_period_from_text(message)
        report = generate_financial_report(db, memory_db, period, model=model)
        result = handle_query(
            report_data=report.model_dump(mode="json"),
            text=message,
            profile_memories_text=profile_memories_text,
            long_term_memories_text=long_term_memories_text,
            conversation_context_text=conversation_context_text,
            model=model,
        )
    elif intent == Intent.REPORT:
        period = _infer_period_from_text(message)
        result = handle_report(
            db=db,
            memory_db=memory_db,
            text=message,
            period=period,
            profile_memories_text=profile_memories_text,
            long_term_memories_text=long_term_memories_text,
            conversation_context_text=conversation_context_text,
            model=model,
        )
    else:
        result = handle_chat(
            text=message,
            profile_memories_text=profile_memories_text,
            long_term_memories_text=long_term_memories_text,
            conversation_context_text=conversation_context_text,
            model=model,
        )

    user_message = _save_message(memory_db, conversation.id, MessageRole.USER, message)
    assistant_message = _save_message(
        memory_db,
        conversation.id,
        MessageRole.ASSISTANT,
        result["reply"],
        actions_json=json.dumps(result.get("actions", []), ensure_ascii=False),
    )

    updated_recent_messages = _get_recent_messages(memory_db, conversation.id, limit=12)
    distilled_memories = distill_long_term_memories(
        memory_db=memory_db,
        session_id=session_id,
        recent_messages=updated_recent_messages,
        profile_memories=profile_memories,
        related_long_term_memories=long_term_memories,
        model=model,
    )

    actions = list(result.get("actions", []))
    for memory in distilled_memories:
        actions.append({"type": "memory_updated", "detail": memory})

    # 只把真正被带入上下文的记忆暴露给调用方，方便外部系统调试 Agent 行为。
    memories_used = [
        f"[公司画像] {memory.category}: {memory.content[:60]}"
        for memory in profile_memories
    ]
    memories_used.extend(
        [f"[长期记忆] {memory.category}: {memory.content[:60]}" for memory in long_term_memories]
    )

    # 保留局部变量，显式说明当前消息已成功持久化，便于后续排查。
    _ = user_message, assistant_message

    return {
        "reply": result["reply"],
        "session_id": session_id,
        "actions": actions,
        "memories_used": memories_used,
    }


def _infer_period_from_text(text: str) -> str:
    """
    从自然语言中提取报告/查询期间。
    """
    match = re.search(r"\b(\d{4}-\d{2})\b", text)
    if match:
        return match.group(1)

    today = date.today()

    if "上个月" in text:
        if today.month == 1:
            return f"{today.year - 1}-12"
        return f"{today.year}-{today.month - 1:02d}"

    return f"{today.year}-{today.month:02d}"


def _get_or_create_conversation(memory_db: Session, session_id: str) -> Conversation:
    """
    获取或创建会话。
    """
    stmt = select(Conversation).where(Conversation.session_id == session_id)
    conversation = memory_db.scalar(stmt)
    if conversation is not None:
        return conversation

    conversation = Conversation(session_id=session_id)
    memory_db.add(conversation)
    memory_db.commit()
    memory_db.refresh(conversation)
    return conversation


def _get_recent_messages(
    memory_db: Session,
    conversation_id: int,
    limit: int = 10,
) -> list[Message]:
    """
    获取最近若干条对话消息，按时间正序返回。
    """
    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    messages = list(memory_db.scalars(stmt).all())
    messages.reverse()
    return messages


def _save_message(
    memory_db: Session,
    conversation_id: int,
    role: MessageRole,
    content: str,
    actions_json: str | None = None,
) -> Message:
    """
    保存单条会话消息。
    """
    message = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        actions_json=actions_json,
    )
    memory_db.add(message)
    memory_db.commit()
    memory_db.refresh(message)
    return message
