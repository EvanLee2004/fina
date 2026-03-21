"""
FastAPI 应用入口。

当前项目已经切换为由外部平台统一处理管理员认证，
本文件不再注册任何本地登录路由。
同时会在应用启动时自动执行建表逻辑。
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from core.database import Base, engine

# 导入所有模型，确保 SQLAlchemy 在 create_all 时能够识别所有数据表。
# 这些导入的主要目的不是直接在本文件中使用，而是触发表结构注册到 Base.metadata。
from models.account import Account  # noqa: F401
from models.receivable import Receivable  # noqa: F401
from models.report import Report  # noqa: F401
from models.voucher import Voucher, VoucherEntry  # noqa: F401
from routers.accounts import router as accounts_router
from routers.ai import router as ai_router
from routers.receivables import router as receivables_router
from routers.reports import router as reports_router
from routers.vouchers import router as vouchers_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    """
    FastAPI 生命周期管理器。

    应用启动时自动执行 Base.metadata.create_all(engine)，
    用于在数据库中创建当前已定义但尚不存在的数据表。
    """
    # 在服务启动阶段执行建表。
    # create_all 只会创建不存在的表，不会覆盖已有表结构。
    Base.metadata.create_all(bind=engine)
    yield

# 创建 FastAPI 应用实例。
# 具体的管理员令牌校验放在各个 router 的 Depends(verify_token) 中处理。
app = FastAPI(
    title="Fina API",
    description="ohao 平台财务管理后端 API",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/ping")
def ping() -> dict[str, str]:
    """
    最小健康检查接口。

    用于确认服务进程已经启动成功，
    也方便后续部署或容器编排时做存活探测。
    """
    return {"message": "pong"}


# 注册所有业务路由。
# 当前各个 router 主要提供接口骨架，用于先让 /docs 正常展示完整 API。
app.include_router(accounts_router)
app.include_router(vouchers_router)
app.include_router(ai_router)
app.include_router(reports_router)
app.include_router(receivables_router)
