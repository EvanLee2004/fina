"""
统一对话路由。

这是外部 AI 或用户与 Fina 财务数字员工交互的唯一入口。
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.auth import verify_token
from core.database import get_db
from core.memory_database import get_memory_db
from schemas.chat import ActionRecord, ChatRequest, ChatResponse
from services.agent.chat_service import chat

router = APIRouter(
    prefix="/api/agent",
    tags=["Agent Chat"],
    dependencies=[Depends(verify_token)],
)


@router.post("/chat", response_model=ChatResponse)
def agent_chat(
    req: ChatRequest,
    db: Session = Depends(get_db),
    memory_db: Session = Depends(get_memory_db),
):
    """
    与财务数字员工对话。

    这是 Fina 的核心接口。发送一条消息，Fina 会：
    - 理解你的意图（记账、查询、报告、闲聊）
    - 加载对这家企业的记忆
    - 给出专业的财务回复
    - 自动沉淀有价值的业务信息为长期记忆
    """
    try:
        result = chat(
            db=db,
            memory_db=memory_db,
            session_id=req.session_id,
            message=req.message,
            model=req.model,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI 服务异常：{e}")

    return ChatResponse(
        reply=result["reply"],
        session_id=result["session_id"],
        actions=[ActionRecord(**a) for a in result.get("actions", [])],
        memories_used=result.get("memories_used", []),
    )
