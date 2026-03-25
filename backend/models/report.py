"""
AI 财务报告归档表模型定义。

这个文件的职责是：
1. 定义 reports 表，用于保存 AI 生成的财务分析报告。
2. 记录报告所属期间和具体文字内容。
3. 为后续报告查询、归档、展示提供 ORM 模型。
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class Report(Base):
    """
    财务报告 ORM 模型。

    这个模型会映射到 PostgreSQL 中的 reports 表。
    每一条记录表示一份 AI 生成并存档的财务分析报告。
    """

    # 指定数据库中的表名。
    __tablename__ = "reports"

    # 报告主键 ID。
    # 使用自增整数作为内部主键，便于查询和排序。
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="报告主键 ID",
    )

    # 报告期间。
    # 按你的要求使用类似 2024-03 的字符串格式表示月份。
    period: Mapped[str] = mapped_column(
        String(7),
        nullable=False,
        index=True,
        comment="报告月份，格式例如 2024-03",
    )

    # 报告内容。
    # 使用 Text 存储 AI 生成的完整文字内容，避免长度受限。
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="AI 生成的报告文字内容",
    )

    # 客观财务数据快照。
    # 这里保存报告生成当下的结构化汇总 JSON，便于 Excel/Word 导出复用。
    objective_json: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="客观财务数据快照 JSON",
    )

    # 报告创建时间。
    # 默认记录当前 UTC 时间，便于后续按生成时间排序与追踪。
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="报告创建时间",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="报告更新时间",
    )
