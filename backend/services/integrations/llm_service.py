"""
AI 服务层。

这个模块负责所有和模型交互的基础能力：
1. 调用 OpenAI 兼容聊天补全接口。
2. 解析严格 JSON 响应。
3. 处理自然语言记账草稿生成。
4. 提供一些跨服务复用的 AI 辅助函数。
"""

from __future__ import annotations

import json
import re
from datetime import date
from decimal import Decimal
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.config import settings
from models.accounting_policy import AccountingPolicy
from models.account import Account


def _get_configured_allowed_models() -> list[str]:
    """
    解析环境变量中的模型白名单。

    这里使用逗号分隔字符串，是为了兼容 `.env`、Docker Compose
    和常见云平台环境变量配置，避免引入额外的 JSON 解析负担。
    """
    raw_models = settings.AI_ALLOWED_MODELS.strip()
    if not raw_models:
        return []

    models: list[str] = []
    for item in raw_models.split(","):
        model_name = item.strip()
        if model_name and model_name not in models:
            models.append(model_name)
    return models


def resolve_ai_model(requested_model: str | None = None) -> str:
    """
    解析本次请求最终要使用的模型。

    规则：
    1. 如果请求显式传了 model，优先使用它。
    2. 否则回退到配置里的默认模型 settings.AI_MODEL。
    3. 如果设置了白名单，则请求模型必须命中白名单。
    """
    candidate = (requested_model or settings.AI_MODEL).strip()
    if not candidate:
        raise ValueError("当前没有可用的模型配置，请检查 AI_MODEL。")

    allowed_models = _get_configured_allowed_models()
    if allowed_models and candidate not in allowed_models:
        raise ValueError(
            f"请求的模型 `{candidate}` 不在允许列表中：{', '.join(allowed_models)}"
        )

    return candidate


def get_ai_model_catalog() -> dict[str, Any]:
    """
    返回当前后端模型配置说明。

    `configured_allowed_models` 是真正用于限制请求的白名单；
    `example_models` 只是给前端或调用方参考的常见 OpenAI 兼容模型示例。
    """
    return {
        "default_model": resolve_ai_model(),
        "configured_allowed_models": _get_configured_allowed_models(),
        "example_models": [
            "deepseek-chat",
            "deepseek-reasoner",
            "gpt-4o-mini",
            "gpt-4.1-mini",
            "qwen-max",
            "qwen-plus",
            "glm-4.5-air",
            "moonshot-v1-8k",
        ],
        "base_url": settings.AI_BASE_URL,
    }


def _build_chat_completions_url() -> str:
    """
    拼出 OpenAI 兼容聊天补全接口地址。
    """
    return f"{settings.AI_BASE_URL.rstrip('/')}/chat/completions"


def _call_ai_chat_completion(
    system_prompt: str,
    user_prompt: str,
    model: str | None = None,
) -> str:
    """
    调用 OpenAI 兼容聊天补全接口。

    这里统一收口网络交互逻辑，其他 service 只关心输入 Prompt 和返回文本。
    """
    if not settings.AI_API_KEY:
        raise ValueError("AI_API_KEY 未配置。")

    payload = {
        "model": resolve_ai_model(model),
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }

    with httpx.Client(timeout=60.0) as client:
        response = client.post(
            _build_chat_completions_url(),
            headers={
                "Authorization": f"Bearer {settings.AI_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()

    response_data = response.json()
    try:
        return response_data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("AI 接口返回结果格式异常。") from exc


def _extract_json_object(content: str) -> dict[str, Any]:
    """
    从模型文本中提取一个 JSON 对象。

    有些模型即使被要求返回 JSON，也可能包一层 Markdown 代码块，
    所以这里统一做一次清洗和兜底解析。
    """
    cleaned = content.strip()

    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError("AI 返回内容不是合法 JSON。") from exc

    if not isinstance(parsed, dict):
        raise ValueError("AI 返回的 JSON 顶层必须是对象。")

    return parsed


def _validate_balance(entries: list[dict[str, Any]]) -> None:
    """
    校验凭证草稿借贷平衡。

    这是自然语言记账进入后续确认/落库前最基础的财务约束。
    """
    if not entries:
        raise ValueError("AI 返回的分录列表不能为空。")

    total_debit = sum((Decimal(str(entry["debit"])) for entry in entries), Decimal("0.00"))
    total_credit = sum((Decimal(str(entry["credit"])) for entry in entries), Decimal("0.00"))

    if total_debit != total_credit:
        raise ValueError("AI 解析结果借贷不平衡。")


def _build_accounts_prompt(db: Session) -> str:
    """
    读取所有启用中的科目，格式化为 Prompt 文本。

    由于当前项目是单公司模式，因此这里直接读取全局启用科目即可。
    """
    statement = (
        select(Account)
        .where(Account.is_active.is_(True))
        .order_by(Account.code.asc(), Account.id.asc())
    )
    accounts = list(db.scalars(statement).all())

    if not accounts:
        raise ValueError("当前没有可用的启用科目，无法进行 AI 记账。")

    lines = []
    for account in accounts:
        lines.append(
            f"id={account.id}, code={account.code}, name={account.name}, type={account.type.value}"
        )
    return "\n".join(lines)


def _build_accounting_policy_prompt(db: Session) -> tuple[str, bool]:
    """
    读取当前公司会计政策，并格式化为 Prompt 文本。

    返回值说明：
    - 第一个值：适合直接拼进 Prompt 的说明文本
    - 第二个值：是否已经完成了正式的会计准则配置
    """
    policy = db.scalar(select(AccountingPolicy).order_by(AccountingPolicy.id.asc()))
    if policy is None or policy.accounting_standard is None:
        return (
            "当前尚未配置正式会计准则与公司会计政策。"
            "你只能输出一个保守的、必须人工确认的凭证草稿，"
            "并且 needs_confirmation 必须为 true。",
            False,
        )

    policy_lines = [
        f"公司名称：{policy.company_name or '未填写'}",
        f"会计准则：{policy.accounting_standard.value}",
        f"纳税人类型：{policy.taxpayer_type.value if policy.taxpayer_type else '未填写'}",
        f"记账币种：{policy.currency}",
        f"人工确认要求：{'必须人工确认' if policy.require_manual_confirmation else '允许人工复核后快速通过'}",
        f"补充说明：{policy.notes or '无'}",
    ]
    return "\n".join(policy_lines), True


def _validate_entries_against_accounts(db: Session, entries: list[dict[str, Any]]) -> None:
    """
    校验 AI 返回的分录是否引用了真实、启用中的科目。

    这样即使模型“看起来”返回了合法 JSON，
    也不能绕过后端对业务口径的校验。
    """
    valid_account_ids = {
        account_id
        for account_id in db.scalars(
            select(Account.id).where(Account.is_active.is_(True))
        ).all()
    }

    if not valid_account_ids:
        raise ValueError("当前没有启用中的科目。")

    for entry in entries:
        account_id = entry.get("account_id")
        if account_id not in valid_account_ids:
            raise ValueError(f"AI 返回了不存在或未启用的科目 ID：{account_id}")

        debit = Decimal(str(entry.get("debit", 0)))
        credit = Decimal(str(entry.get("credit", 0)))

        # 每条分录必须恰好一边有值，另一边为 0，避免模型给出双边同时记数的脏数据。
        if debit < 0 or credit < 0:
            raise ValueError("AI 返回的分录金额不能为负数。")
        if (debit == 0 and credit == 0) or (debit > 0 and credit > 0):
            raise ValueError("每条分录必须且只能有借方或贷方一侧有金额。")


def parse_natural_language(
    db: Session,
    text: str,
    model: str | None = None,
) -> dict[str, Any]:
    """
    将自然语言描述解析成凭证草稿。

    返回的只是草稿，不会直接写入数据库。
    """
    accounts_prompt = _build_accounts_prompt(db)
    policy_prompt, policy_configured = _build_accounting_policy_prompt(db)

    system_prompt = (
        "你是专业会计助手。"
        "你必须根据提供的科目表，把用户的中文业务描述解析成会计凭证草稿。"
        "如果业务事实不完整，就必须明确提示假设和风险。"
        "你只能返回严格 JSON，不要返回解释、Markdown 或额外文字。"
    )

    user_prompt = f"""
今天日期：{date.today().isoformat()}

公司会计政策：
{policy_prompt}

完整科目表：
{accounts_prompt}

用户输入：
{text}

请只返回严格 JSON，格式如下：
{{
  "date": "2026-03-25",
  "memo": "摘要",
  "entries": [
    {{
      "account_id": 1,
      "debit": 1000,
      "credit": 0
    }},
    {{
      "account_id": 2,
      "debit": 0,
      "credit": 1000
    }}
  ],
  "confidence": 0.78,
  "needs_confirmation": true,
  "assumptions": ["如未提供发票信息，默认按常规经营支出处理"],
  "warnings": ["当前业务描述没有说明税额与发票类型"]
}}

要求：
1. account_id 只能从给定科目表中选择
2. 分录至少两条
3. 所有分录必须借贷平衡
4. 每条分录只能有一侧金额
5. 不确定时采用最保守、最常见的会计处理
6. 如果存在假设、政策未配置或业务事实不完整，needs_confirmation 必须为 true
7. confidence 取值范围必须在 0 到 1 之间
""".strip()

    content = _call_ai_chat_completion(system_prompt, user_prompt, model=model)
    parsed = _extract_json_object(content)

    required_keys = {"date", "memo", "entries"}
    if not required_keys.issubset(parsed.keys()):
        raise ValueError("AI 返回的 JSON 缺少必要字段。")

    entries = parsed.get("entries")
    if not isinstance(entries, list):
        raise ValueError("AI 返回的 entries 必须是列表。")

    _validate_balance(entries)
    _validate_entries_against_accounts(db, entries)

    confidence = float(parsed.get("confidence", 0.0))
    if confidence < 0 or confidence > 1:
        raise ValueError("AI 返回的 confidence 必须在 0 到 1 之间。")

    assumptions = [str(item).strip() for item in parsed.get("assumptions", []) if str(item).strip()]
    warnings = [str(item).strip() for item in parsed.get("warnings", []) if str(item).strip()]
    needs_confirmation = bool(parsed.get("needs_confirmation", False))

    # 如果公司还没正式配置会计准则，或者模型自己承认存在假设，
    # 就强制把草稿降级为“待人工确认”，避免误以为它已经可以直接记账。
    if not policy_configured:
        needs_confirmation = True
        warnings.insert(0, "当前尚未配置会计准则与公司会计政策，草稿仅供人工确认。")

    if assumptions or confidence < 0.85:
        needs_confirmation = True

    parsed["confidence"] = confidence
    parsed["needs_confirmation"] = needs_confirmation
    parsed["assumptions"] = assumptions
    parsed["warnings"] = warnings
    return parsed
