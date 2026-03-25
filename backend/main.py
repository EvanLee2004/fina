"""
Fina - AI 财务数字员工。

核心入口：POST /api/agent/chat
同时保留原有 CRUD 接口供直接数据访问。
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from core.database import Base, engine
from core.memory_database import MemoryBase, memory_engine

# 导入所有模型，触发表结构注册到 Base.metadata。
from models.account import Account  # noqa: F401
from models.accounting_policy import AccountingPolicy  # noqa: F401
from models.conversation import Conversation, Message  # noqa: F401
from models.integration_event import IntegrationEvent  # noqa: F401
from models.memory import Memory  # noqa: F401
from models.receivable import Receivable  # noqa: F401
from models.report import Report  # noqa: F401
from models.voucher import Voucher, VoucherEntry  # noqa: F401
from routers.accounts import router as accounts_router
from routers.ai import router as ai_router
from routers.chat import router as chat_router
from routers.exports import router as exports_router
from routers.policy import router as policy_router
from routers.receivables import router as receivables_router
from routers.reports import router as reports_router
from routers.stripe import router as stripe_router
from routers.vouchers import router as vouchers_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    # 主库负责财务业务数据。
    Base.metadata.create_all(bind=engine)

    # 记忆库负责对话历史与长期记忆。
    MemoryBase.metadata.create_all(bind=memory_engine)
    yield


app = FastAPI(
    title="Fina API",
    description="AI 财务数字员工 — 像真正的会计一样理解你的业务",
    version="0.2.0",
    lifespan=lifespan,
)


@app.get("/ping")
def ping() -> dict[str, str]:
    return {"message": "pong"}


# 核心对话接口
app.include_router(chat_router)

# 原有 CRUD 接口
app.include_router(accounts_router)
app.include_router(vouchers_router)
app.include_router(ai_router)
app.include_router(reports_router)
app.include_router(receivables_router)
app.include_router(exports_router)
app.include_router(policy_router)
app.include_router(stripe_router)
