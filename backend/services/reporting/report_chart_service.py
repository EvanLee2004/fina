"""
财务报告图表服务。

这个模块专门负责：
1. 使用 matplotlib 生成报告配图。
2. 处理中文字体选择，尽量避免图表中的中文出现乱码或方块字。
3. 为 Word 报告提供稳定的 PNG 图片资源。

设计说明：
- 图表属于“报告交付层”的一部分，因此不直接和数据库耦合。
- 统一接收结构化的财务摘要，输出图片路径，便于 Word 报告复用。
"""

from __future__ import annotations

import os
from pathlib import Path

from core.config import settings

# matplotlib 在 import 阶段就会尝试初始化配置目录。
# 如果不在这里提前指定一个明确且可写的目录，某些服务器、Docker 容器
# 或受限执行环境里就会因为默认缓存目录不可写而直接导入失败。
_MATPLOTLIB_CONFIG_DIR = Path(settings.EXPORTS_DIR) / ".matplotlib"
_MATPLOTLIB_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_MATPLOTLIB_CONFIG_DIR))

import matplotlib

# 使用无界面渲染后端，保证在服务器和 Docker 容器中都可以正常出图。
matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.font_manager import FontProperties

from schemas.report import FinancialObjectiveSummary

# 让负号在中文字体环境下正常显示。
plt.rcParams["axes.unicode_minus"] = False


def _ensure_chart_dir(period: str) -> Path:
    """
    为指定报告期间准备图表目录。
    """
    export_dir = Path(settings.EXPORTS_DIR)
    chart_dir = export_dir / "charts" / period
    chart_dir.mkdir(parents=True, exist_ok=True)
    return chart_dir


def _pick_chinese_font() -> FontProperties | None:
    """
    选择一个可用的中文字体。

    这里优先按“常见系统字体文件路径”做显式匹配，
    这样在 macOS 和 Docker 环境里都更稳定。
    """
    candidate_paths = [
        # macOS 常见中文字体。
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
        # Linux / Docker 中安装 fonts-noto-cjk 后的常见路径。
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    ]

    for font_path in candidate_paths:
        path = Path(font_path)
        if path.exists():
            return FontProperties(fname=str(path))

    # 如果显式路径都找不到，再尝试根据字体家族名搜索。
    fallback_names = [
        "Hiragino Sans GB",
        "STHeiti",
        "PingFang SC",
        "Arial Unicode MS",
        "Noto Sans CJK SC",
        "Noto Sans CJK",
        "Microsoft YaHei",
        "SimHei",
    ]

    for font_name in fallback_names:
        try:
            matched_path = font_manager.findfont(font_name, fallback_to_default=False)
        except Exception:
            continue

        if matched_path and Path(matched_path).exists():
            return FontProperties(fname=matched_path)

    return None


def _apply_axis_font(ax, font_properties: FontProperties | None) -> None:
    """
    把选中的中文字体统一应用到坐标轴文字。
    """
    if font_properties is None:
        return

    ax.title.set_fontproperties(font_properties)
    ax.xaxis.label.set_fontproperties(font_properties)
    ax.yaxis.label.set_fontproperties(font_properties)

    for label in ax.get_xticklabels():
        label.set_fontproperties(font_properties)
    for label in ax.get_yticklabels():
        label.set_fontproperties(font_properties)


def generate_financial_charts(
    period: str,
    summary: FinancialObjectiveSummary,
) -> list[str]:
    """
    生成 Word 报告使用的图表图片。

    当前默认输出两张图：
    1. 关键指标柱状图
    2. 应收/应付账龄对比图
    """
    chart_dir = _ensure_chart_dir(period)
    font_properties = _pick_chinese_font()

    chart_paths = [
        _generate_metric_chart(chart_dir, period, summary, font_properties),
        _generate_aging_chart(chart_dir, period, summary, font_properties),
    ]

    return [str(path.resolve()) for path in chart_paths if path is not None]


def _generate_metric_chart(
    chart_dir: Path,
    period: str,
    summary: FinancialObjectiveSummary,
    font_properties: FontProperties | None,
) -> Path:
    """
    生成关键指标柱状图。
    """
    labels = ["收入", "支出", "净利润", "待收款", "待付款"]
    values = [
        float(summary.total_revenue),
        float(summary.total_expense),
        float(summary.net_profit),
        float(summary.pending_receivables),
        float(summary.pending_payables),
    ]
    colors = ["#2B6CB0", "#DD6B20", "#2F855A", "#805AD5", "#C05621"]

    figure, ax = plt.subplots(figsize=(10, 5.2))
    ax.bar(labels, values, color=colors)
    ax.set_title(f"{period} 关键财务指标")
    ax.set_ylabel("金额")
    ax.grid(axis="y", linestyle="--", alpha=0.25)
    _apply_axis_font(ax, font_properties)

    # 在柱子顶部标注数值，便于管理层快速阅读。
    for index, value in enumerate(values):
        ax.text(
            index,
            value,
            f"{value:,.2f}",
            ha="center",
            va="bottom",
            fontsize=9,
            fontproperties=font_properties,
        )

    figure.tight_layout()
    output_path = chart_dir / f"{period}-metrics.png"
    figure.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(figure)
    return output_path


def _generate_aging_chart(
    chart_dir: Path,
    period: str,
    summary: FinancialObjectiveSummary,
    font_properties: FontProperties | None,
) -> Path:
    """
    生成应收/应付账龄对比图。
    """
    labels = [bucket.label for bucket in summary.receivable_aging]
    receivable_values = [float(bucket.amount) for bucket in summary.receivable_aging]
    payable_values = [float(bucket.amount) for bucket in summary.payable_aging]

    figure, ax = plt.subplots(figsize=(10, 5.2))
    x_positions = range(len(labels))
    width = 0.36

    ax.bar(
        [position - width / 2 for position in x_positions],
        receivable_values,
        width=width,
        label="应收",
        color="#3182CE",
    )
    ax.bar(
        [position + width / 2 for position in x_positions],
        payable_values,
        width=width,
        label="应付",
        color="#ED8936",
    )

    ax.set_title(f"{period} 账龄结构对比")
    ax.set_xlabel("账龄区间")
    ax.set_ylabel("金额")
    ax.set_xticks(list(x_positions))
    ax.set_xticklabels(labels)
    ax.grid(axis="y", linestyle="--", alpha=0.25)
    legend = ax.legend()
    _apply_axis_font(ax, font_properties)
    if font_properties is not None:
        for text in legend.get_texts():
            text.set_fontproperties(font_properties)

    figure.tight_layout()
    output_path = chart_dir / f"{period}-aging.png"
    figure.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(figure)
    return output_path
