"""
财务大脑服务。

这个模块负责把：
1. 客观财务数据
2. 公司画像
3. 长期记忆
4. 最近对话上下文

整合后交给模型，生成最终回复。

这一版不再让主回复链路顺便产出长期记忆，
而是把“回复”和“记忆蒸馏”拆开，避免模型同时做两件事导致输出不稳定。
"""

from __future__ import annotations

import json
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from services.integrations.llm_service import (
    _call_ai_chat_completion,
    _extract_json_object,
    _validate_balance,
    parse_natural_language,
)
from services.reporting.export_excel_service import export_financial_excel
from services.reporting.export_word_service import export_financial_word_report
from services.reporting.report_service import (
    build_financial_objective_summary,
    generate_financial_report,
)


def _build_system_prompt(
    profile_memories_text: str,
    long_term_memories_text: str,
    conversation_context_text: str,
) -> str:
    """
    构建统一系统提示词。

    这里把公司画像、长期记忆和最近对话统一注入，
    让模型回复更像“持续理解企业情况的财务数字员工”。
    """
    return f"""你是 Fina，一个面向单一企业长期服务的财务数字员工。
你的角色像一个真正的会计和财务助理，不只是回答问题，还会结合公司背景理解业务。

## 公司画像
{profile_memories_text}

## 相关长期记忆
{long_term_memories_text}

## 最近对话
{conversation_context_text}

## 回答原则
1. 不编造客观数据。
2. 财务数字必须以给定数据为准。
3. 不确定的业务事实要明确说明，而不是瞎猜。
4. 回复要用中文，专业、简洁、可执行。
5. 如果用户明确要求导出文件，可以触发导出动作。
"""


def handle_record(
    db: Session,
    text: str,
    profile_memories_text: str,
    long_term_memories_text: str,
    conversation_context_text: str,
    model: str | None = None,
) -> dict[str, Any]:
    """
    处理记账意图。

    这里优先使用后端的记账解析能力生成凭证草稿，
    再让模型基于草稿做中文确认说明。
    """
    draft = parse_natural_language(db, text, model=model)
    _validate_balance(draft["entries"])

    system_prompt = _build_system_prompt(
        profile_memories_text=profile_memories_text,
        long_term_memories_text=long_term_memories_text,
        conversation_context_text=conversation_context_text,
    )

    user_prompt = f"""
用户想记一笔账。

用户原话：
{text}

系统已经解析出的凭证草稿：
{json.dumps(draft, ensure_ascii=False)}

请只返回严格 JSON：
{{
  "reply": "一段中文确认回复"
}}
""".strip()

    content = _call_ai_chat_completion(system_prompt, user_prompt, model=model)
    parsed = _extract_json_object(content)

    needs_confirmation = bool(draft.get("needs_confirmation", True))
    confidence = float(draft.get("confidence", 0.0))
    assumptions = draft.get("assumptions", [])
    warnings = draft.get("warnings", [])

    action_type = (
        "voucher_draft_pending_confirmation"
        if needs_confirmation
        else "voucher_draft_ready"
    )

    return {
        "reply": parsed.get(
            "reply",
            "已生成待确认凭证草稿。"
            if needs_confirmation
            else "已生成凭证草稿，可继续人工复核。",
        ),
        "actions": [
            {
                "type": action_type,
                "detail": {
                    **draft,
                    "confidence": confidence,
                    "assumptions": assumptions,
                    "warnings": warnings,
                },
            }
        ],
    }


def handle_query(
    report_data: dict[str, Any],
    text: str,
    profile_memories_text: str,
    long_term_memories_text: str,
    conversation_context_text: str,
    model: str | None = None,
) -> dict[str, Any]:
    """
    处理财务查询意图。

    查询本质上仍然围绕客观财务汇总展开，因此直接复用统一报告结果。
    """
    system_prompt = _build_system_prompt(
        profile_memories_text=profile_memories_text,
        long_term_memories_text=long_term_memories_text,
        conversation_context_text=conversation_context_text,
    )

    user_prompt = f"""
用户问题：
{text}

可用财务报告：
{json.dumps(report_data, ensure_ascii=False)}

请只返回严格 JSON：
{{
  "reply": "根据数据直接回答用户的问题"
}}
""".strip()

    content = _call_ai_chat_completion(system_prompt, user_prompt, model=model)
    parsed = _extract_json_object(content)

    return {
        "reply": parsed.get("reply", "已完成查询。"),
        "actions": [{"type": "financial_query", "detail": {"period": report_data["period"]}}],
    }


def handle_report(
    db: Session,
    memory_db: Session,
    text: str,
    period: str,
    profile_memories_text: str,
    long_term_memories_text: str,
    conversation_context_text: str,
    model: str | None = None,
) -> dict[str, Any]:
    """
    处理报告/导出意图。

    如果用户明确提到 Excel 或 Word，就在生成报告的同时触发导出。
    """
    report = generate_financial_report(db, memory_db, period, model=model)
    objective_data = build_financial_objective_summary(db, period)
    actions: list[dict[str, Any]] = [
        {"type": "report_generated", "detail": {"period": period}},
    ]

    normalized_text = text.lower()
    exported_files = []

    # 用户一旦明确提到 excel/xlsx，就立即生成 Excel 导出文件。
    if any(keyword in normalized_text for keyword in ["excel", "xlsx", "表格"]):
        excel_file = export_financial_excel(
            db=db,
            memory_db=memory_db,
            period=period,
            report=report,
            objective_data=objective_data,
            model=model,
        )
        exported_files.append(excel_file.model_dump())
        actions.append({"type": "excel_exported", "detail": excel_file.model_dump()})

    # 用户一旦明确提到 word/doc/docx/文档，就立即生成 Word 报告。
    if any(keyword in normalized_text for keyword in ["word", "doc", "docx", "文档"]):
        word_file = export_financial_word_report(
            db=db,
            memory_db=memory_db,
            period=period,
            report=report,
            model=model,
        )
        exported_files.append(word_file.model_dump())
        actions.append({"type": "word_report_exported", "detail": word_file.model_dump()})

    system_prompt = _build_system_prompt(
        profile_memories_text=profile_memories_text,
        long_term_memories_text=long_term_memories_text,
        conversation_context_text=conversation_context_text,
    )
    user_prompt = f"""
用户请求：
{text}

可用财务报告：
{json.dumps(report.model_dump(mode="json"), ensure_ascii=False)}

已导出的文件：
{json.dumps(exported_files, ensure_ascii=False)}

请只返回严格 JSON：
{{
  "reply": "告诉用户报告已经生成，并说明如果有文件导出则文件已准备好"
}}
""".strip()

    content = _call_ai_chat_completion(system_prompt, user_prompt, model=model)
    parsed = _extract_json_object(content)

    return {
        "reply": parsed.get("reply", report.content),
        "actions": actions,
    }


def handle_chat(
    text: str,
    profile_memories_text: str,
    long_term_memories_text: str,
    conversation_context_text: str,
    model: str | None = None,
) -> dict[str, Any]:
    """
    处理一般业务沟通/闲聊意图。
    """
    system_prompt = _build_system_prompt(
        profile_memories_text=profile_memories_text,
        long_term_memories_text=long_term_memories_text,
        conversation_context_text=conversation_context_text,
    )

    user_prompt = f"""
用户消息：
{text}

请只返回严格 JSON：
{{
  "reply": "你的中文回复"
}}
""".strip()

    content = _call_ai_chat_completion(system_prompt, user_prompt, model=model)
    parsed = _extract_json_object(content)

    return {
        "reply": parsed.get("reply", "已收到。"),
        "actions": [],
    }
