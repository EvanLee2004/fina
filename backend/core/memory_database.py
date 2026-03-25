"""
记忆数据库连接与 Session 管理模块。

这个模块和主财务数据库分开，专门负责：
1. 存放对话会话与消息历史。
2. 存放经过提炼后的长期记忆。
3. 为后续记忆策略重构保留独立边界，避免和财务主账数据耦合。

设计说明：
- 如果配置了 MEMORY_DATABASE_URL，就使用独立记忆库。
- 如果没有配置，则回退到主库 DATABASE_URL，便于本地快速启动。
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from core.config import settings

# 优先使用独立记忆库；未配置时回退到主数据库，保证开发环境可直接运行。
MEMORY_DATABASE_URL = settings.MEMORY_DATABASE_URL or settings.DATABASE_URL

# 记忆库 engine。
# 这里沿用和主库相同的连接池策略，减少连接断开导致的异常。
memory_engine: Engine = create_engine(
    MEMORY_DATABASE_URL,
    pool_pre_ping=True,
    future=True,
)

# 记忆库 Session 工厂。
MemorySessionLocal = sessionmaker(
    bind=memory_engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    class_=Session,
)

# 记忆库 ORM Base。
MemoryBase = declarative_base()


def get_memory_db():
    """
    FastAPI 依赖注入用的记忆库 Session 生成器。

    每个请求拿到一个独立 Session，
    请求结束后统一关闭，避免连接泄漏。
    """
    db = MemorySessionLocal()
    try:
        yield db
    finally:
        db.close()
