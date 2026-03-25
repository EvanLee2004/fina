"""
终端聊天入口脚本。

这个脚本让你可以直接在终端里和 Fina 对话，
不需要额外先写 curl 或手动拼 HTTP 请求。
"""

from __future__ import annotations

import sys
from pathlib import Path

# 把 backend 目录加入模块搜索路径，保证脚本从项目根目录执行时也能正常导入。
PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from core.database import SessionLocal
from core.memory_database import MemorySessionLocal
from services.agent.chat_service import chat


def main() -> None:
    """
    启动终端对话循环。
    """
    session_id = input("请输入会话 ID（直接回车则自动生成）：").strip() or None
    model = input("请输入模型名（直接回车则使用默认模型）：").strip() or None

    print("输入内容后回车即可对话，输入 exit 结束。")

    db = SessionLocal()
    memory_db = MemorySessionLocal()
    try:
        while True:
            message = input("\n你：").strip()
            if not message:
                continue
            if message.lower() in {"exit", "quit"}:
                break

            result = chat(
                db=db,
                memory_db=memory_db,
                session_id=session_id,
                message=message,
                model=model,
            )
            session_id = result["session_id"]
            print(f"Fina：{result['reply']}")
            if result.get("actions"):
                print(f"动作：{result['actions']}")
    finally:
        memory_db.close()
        db.close()


if __name__ == "__main__":
    main()
