"""
意图识别服务。

从用户消息中识别意图，决定后续走哪条处理路径。
"""

from __future__ import annotations

from enum import Enum


class Intent(str, Enum):
    """用户意图枚举。"""

    # 记账：用户描述了一笔业务交易，需要生成凭证。
    RECORD = "record"

    # 查询：用户问财务数据相关的问题。
    QUERY = "query"

    # 报告：用户要求生成或查看财务报告。
    REPORT = "report"

    # 闲聊/业务沟通：不属于上述三类的对话，可能包含需要记住的业务信息。
    CHAT = "chat"


# 记账关键词
_RECORD_KEYWORDS = [
    "付了", "收到", "支付", "收入", "花了", "买了", "卖了",
    "进账", "转账", "报销", "发票", "采购", "销售",
    "记一笔", "记账", "入账", "开票", "货款", "工资",
    "房租", "水电", "运费", "税", "借款", "还款",
]

# 查询关键词
_QUERY_KEYWORDS = [
    "多少", "查一下", "查询", "看看", "余额", "欠",
    "花了多少", "收了多少", "利润", "亏了", "赚了",
    "应收", "应付", "账龄", "现金流", "费用",
    "哪个客户", "哪个供应商", "占比", "趋势",
]

# 报告关键词
_REPORT_KEYWORDS = [
    "报告", "报表", "月报", "分析", "汇总", "总结",
    "经营情况", "财务状况", "导出", "excel", "xlsx", "word", "docx", "文档",
]


def classify_intent(text: str) -> Intent:
    """
    基于关键词的意图分类。

    优先级：记账 > 报告 > 查询 > 闲聊。
    后续可替换为 AI 分类以提高准确率。
    """
    # 记账意图：包含金额模式 + 记账关键词
    has_amount = any(c.isdigit() for c in text)
    record_hits = sum(1 for kw in _RECORD_KEYWORDS if kw in text)
    if has_amount and record_hits >= 1:
        return Intent.RECORD

    # 报告意图
    report_hits = sum(1 for kw in _REPORT_KEYWORDS if kw in text)
    if report_hits >= 1:
        return Intent.REPORT

    # 查询意图
    query_hits = sum(1 for kw in _QUERY_KEYWORDS if kw in text)
    if query_hits >= 1:
        return Intent.QUERY

    return Intent.CHAT


def extract_keywords(text: str) -> list[str]:
    """从文本中提取用于记忆检索的关键词。"""
    keywords = []

    # 提取所有中文"词"——这里用简单的 bigram + 关键词匹配。
    all_keywords = _RECORD_KEYWORDS + _QUERY_KEYWORDS + _REPORT_KEYWORDS
    for kw in all_keywords:
        if kw in text:
            keywords.append(kw)

    # 提取可能的人名、公司名（简单启发式：连续2-4个中文字符）
    import re
    # 匹配 "客户X"、"供应商X" 等模式
    name_patterns = re.findall(r"(?:客户|供应商|公司)\s*(\S{1,10})", text)
    keywords.extend(name_patterns)

    # 去重
    return list(dict.fromkeys(keywords))
