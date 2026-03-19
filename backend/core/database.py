"""
PostgreSQL 数据库连接与 Session 管理模块。

这个文件的职责是：
1. 从项目根目录的 .env 中读取 DATABASE_URL。
2. 创建 SQLAlchemy 的 engine，连接到 Docker 中运行的 PostgreSQL。
3. 提供 SessionLocal，供 FastAPI 路由或 service 层获取数据库会话。
4. 提供 Base，供后续 SQLAlchemy 模型类继承。
5. 提供 get_db() 依赖函数，便于在 FastAPI 中按请求自动打开/关闭数据库连接。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

# 计算项目根目录。
# 当前文件位置是 backend/core/database.py，
# parents[2] 对应项目根目录 fina/，也就是 .env 所在的位置。
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# 明确指定 .env 的绝对路径，避免因为运行目录不同而读取失败。
ENV_FILE_PATH = PROJECT_ROOT / ".env"


def _load_env_file(env_file_path: Path) -> None:
    """
    手动读取 .env 文件中的键值对，并写入当前进程环境变量。

    这样做的好处是：
    1. 不强依赖 python-dotenv，减少当前阶段的额外依赖。
    2. 即使你从 backend/ 目录单独启动 FastAPI，也能稳定读取项目根目录配置。

    约定：
    - 只解析 `KEY=VALUE` 形式的行。
    - 空行和以 # 开头的注释行会被跳过。
    - 如果某个环境变量已经存在，则不覆盖，优先尊重系统环境变量。
    """
    if not env_file_path.exists():
        return

    for raw_line in env_file_path.read_text(encoding="utf-8").splitlines():
        # 去掉首尾空白，便于统一处理。
        line = raw_line.strip()

        # 跳过空行和注释行。
        if not line or line.startswith("#"):
            continue

        # 如果该行不是标准 KEY=VALUE 格式，则忽略，避免报错影响启动。
        if "=" not in line:
            continue

        key, value = line.split("=", 1)

        # 处理 value 两侧可能存在的单引号或双引号。
        normalized_value = value.strip().strip('"').strip("'")

        # 使用 setdefault 的语义：只有当环境中不存在该变量时才写入。
        os.environ.setdefault(key.strip(), normalized_value)


# 在模块加载时就主动读取 .env，保证后续获取 DATABASE_URL 时有值。
_load_env_file(ENV_FILE_PATH)

# 从环境变量中读取数据库连接地址。
# 这里会读取你在项目根目录 .env 中配置的：
# DATABASE_URL=postgresql://fina:fina123@localhost:5432/fina
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL 未配置。请在项目根目录 .env 中设置数据库连接字符串。"
    )

# 创建 SQLAlchemy engine。
# pool_pre_ping=True 可以在连接池取出连接前做一次可用性检查，
# 能减少数据库连接断开后出现的 stale connection 问题。
# future=True 使用 SQLAlchemy 2.0 风格行为。
engine: Engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    future=True,
)

# 创建 Session 工厂。
# autocommit=False: 事务不会自动提交，必须显式 commit，避免误写入。
# autoflush=False: 避免查询前自动刷盘，方便更可控地管理事务。
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    class_=Session,
)

# 所有 ORM 模型都应继承这个 Base。
# 后续你写 models/user.py、models/account.py 等时，都可以：
# class User(Base): ...
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI 依赖注入用的数据库会话生成器。

    用法示例：
        from fastapi import Depends
        from sqlalchemy.orm import Session
        from backend.core.database import get_db

        @router.get("/users")
        def list_users(db: Session = Depends(get_db)):
            ...

    工作方式：
    - 请求进入时创建一个数据库 Session。
    - 请求结束后无论成功还是异常，都会在 finally 中关闭 Session。
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database_connection() -> bool:
    """
    主动检测数据库连接是否可用。

    返回值：
    - True: 数据库连接成功。
    - False: 数据库连接失败。

    这个函数适合：
    - 应用启动时做一次健康检查
    - 编写 /ping 或 /health 接口时复用
    """
    try:
        with engine.connect() as connection:
            # 执行一条最轻量的 SQL 语句，验证连接链路是通的。
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
