"""
记忆系统服务层。

这一版不再做多租户隔离，而是把“公司画像”和“长期记忆”做成单公司模型：
1. profile 记忆：稳定、基础、每次都应该带入的公司背景信息。
2. long_term 记忆：从对话中提炼出来、以后能复用的经营知识。
3. conversation 日志：完整保留原始对话，用于追溯和后续再提炼。

重要设计：
- 原始对话不直接等于长期记忆。
- 每轮对话结束后，都会让模型做一次“记忆蒸馏”。
- 只有真正重要、可复用、相对稳定的知识才会进入长期记忆库。
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from models.conversation import Message
from models.memory import Memory, MemoryType
from services.integrations.llm_service import _call_ai_chat_completion, _extract_json_object


def get_profile_memories(memory_db: Session) -> list[Memory]:
    """
    获取公司画像记忆。

    这类信息默认每次对话都会带入提示词，
    因为它们描述的是企业长期稳定背景。
    """
    stmt = (
        select(Memory)
        .where(Memory.type == MemoryType.PROFILE)
        .order_by(Memory.category.asc(), Memory.updated_at.desc())
    )
    return list(memory_db.scalars(stmt).all())


def search_long_term_memories(
    memory_db: Session,
    keywords: list[str],
    limit: int = 8,
) -> list[Memory]:
    """
    按关键词检索长期记忆。

    当前仍然采用 LIKE 模糊匹配，优点是：
    - 实现简单，先把长期记忆机制跑通
    - 不引入向量库，降低当前复杂度
    """
    if not keywords:
        return []

    stmt = select(Memory).where(Memory.type == MemoryType.LONG_TERM)

    # 任一关键词命中分类或内容，就认为这条记忆与当前对话相关。
    conditions = []
    for keyword in keywords:
        pattern = f"%{keyword}%"
        conditions.append(Memory.category.ilike(pattern))
        conditions.append(Memory.content.ilike(pattern))

    stmt = (
        stmt.where(or_(*conditions))
        .order_by(Memory.importance.desc(), Memory.updated_at.desc())
        .limit(limit)
    )
    return list(memory_db.scalars(stmt).all())


def format_memories_for_prompt(memories: list[Memory]) -> str:
    """
    把记忆列表格式化成适合提示词直接拼接的文本。

    为了减少模型上下文浪费，这里只保留最核心的信息字段。
    """
    if not memories:
        return "（暂无相关记忆）"

    lines = []
    for memory in memories:
        lines.append(
            f"[{memory.type.value}][{memory.category}][重要度{memory.importance}] {memory.content}"
        )
    return "\n".join(lines)


def format_recent_messages_for_prompt(messages: list[Message]) -> str:
    """
    将最近对话格式化成 Prompt 文本。

    只有最近若干条对话会进入上下文，避免把整段历史都塞给模型。
    """
    if not messages:
        return "（这是一次新对话，暂无历史消息）"

    lines = []
    for message in messages:
        role_name = "用户" if message.role.value == "user" else "助手"
        lines.append(f"{role_name}: {message.content}")
    return "\n".join(lines)


def upsert_memory(
    memory_db: Session,
    memory_type: MemoryType,
    category: str,
    content: str,
    importance: int = 3,
    source: str | None = None,
) -> Memory:
    """
    新增或更新一条记忆。

    合并规则：
    - 同类型 + 同分类视为同一条知识
    - 新内容会覆盖旧内容
    - 重要性取更高值，避免高价值知识被低分覆盖
    """
    stmt = select(Memory).where(
        Memory.type == memory_type,
        Memory.category == category,
    )
    existing = memory_db.scalar(stmt)

    normalized_importance = max(1, min(5, int(importance)))

    if existing is not None:
        existing.content = content
        existing.importance = max(existing.importance, normalized_importance)
        if source:
            existing.source = source
        memory_db.commit()
        memory_db.refresh(existing)
        return existing

    memory = Memory(
        type=memory_type,
        category=category,
        content=content,
        importance=normalized_importance,
        source=source,
    )
    memory_db.add(memory)
    memory_db.commit()
    memory_db.refresh(memory)
    return memory


def distill_long_term_memories(
    memory_db: Session,
    session_id: str,
    recent_messages: list[Message],
    profile_memories: list[Memory],
    related_long_term_memories: list[Memory],
    model: str | None = None,
) -> list[dict[str, Any]]:
    """
    让模型从最近对话中提炼高价值长期记忆。

    注意：
    - 这里不是让模型“记住所有内容”
    - 而是只保留未来可复用、和财务判断相关的知识
    - 无意义寒暄、一次性情绪表达、重复描述都应该直接丢弃
    """
    recent_conversation_text = format_recent_messages_for_prompt(recent_messages)
    profile_text = format_memories_for_prompt(profile_memories)
    long_term_text = format_memories_for_prompt(related_long_term_memories)

    system_prompt = """
你是企业长期记忆整理助手。
你的任务不是记录聊天流水账，而是从最近对话中提炼真正值得长期保存的经营知识。

## 什么值得保存
- 企业主营业务、经营模式、盈利方式
- 重要客户/供应商关系与结算习惯
- 回款周期、付款习惯、账期规律
- 费用结构、经营特征、季节性规律
- 财务风险偏好、报销规则、内部口径
- 明显稳定且未来会反复用到的事实

## 什么不值得保存
- 客套话、寒暄、重复表达
- 一次性的临时情绪
- 没有稳定价值的碎片信息
- 对未来判断没有帮助的废话

你必须返回严格 JSON，格式如下：
{
  "memories": [
    {
      "category": "分类标签",
      "content": "提炼后的长期知识",
      "type": "profile 或 long_term",
      "importance": 1
    }
  ]
}

如果没有值得保存的知识，返回 {"memories": []}。
不要返回任何额外解释。
""".strip()

    user_prompt = f"""
会话 ID：{session_id}

现有公司画像：
{profile_text}

现有相关长期记忆：
{long_term_text}

最近对话：
{recent_conversation_text}

请只提炼真正值得长期保存的知识。
""".strip()

    content = _call_ai_chat_completion(system_prompt, user_prompt, model=model)
    parsed = _extract_json_object(content)

    memories = parsed.get("memories", [])
    if not isinstance(memories, list):
        return []

    saved_results: list[dict[str, Any]] = []
    for memory in memories:
        if not isinstance(memory, dict):
            continue

        category = str(memory.get("category", "")).strip()
        content_text = str(memory.get("content", "")).strip()
        memory_type_str = str(memory.get("type", "long_term")).strip().lower()
        importance = int(memory.get("importance", 3))

        if not category or not content_text:
            continue

        memory_type = (
            MemoryType.PROFILE
            if memory_type_str == MemoryType.PROFILE.value
            else MemoryType.LONG_TERM
        )

        saved = upsert_memory(
            memory_db=memory_db,
            memory_type=memory_type,
            category=category,
            content=content_text,
            importance=importance,
            source=f"conversation:{session_id}",
        )
        saved_results.append(
            {
                "category": saved.category,
                "memory_type": saved.type.value,
                "importance": saved.importance,
            }
        )

    return saved_results
