"""
初始化标准会计科目脚本。

这个脚本专门负责：
1. 连接 PostgreSQL 数据库。
2. 确保 accounts 表已创建。
3. 插入中国小企业常用标准会计科目。
4. 对已存在的科目编码自动跳过，避免重复插入。

运行方式：
    python backend/scripts/init_accounts.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# 把 backend 目录加入 Python 模块搜索路径。
# 这样脚本可以直接导入 core.database 和 models.account。
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select  # noqa: E402

from core.database import Base, SessionLocal, engine  # noqa: E402
from models.account import Account, AccountType  # noqa: E402

# 预置的标准会计科目。
# 这里按你给定的资产、负债、所有者权益、收入、成本、费用分类录入。
STANDARD_ACCOUNTS = [
    # 资产类
    {"code": "1001", "name": "库存现金", "type": AccountType.ASSET},
    {"code": "1002", "name": "银行存款", "type": AccountType.ASSET},
    {"code": "1122", "name": "应收账款", "type": AccountType.ASSET},
    {"code": "1123", "name": "预付账款", "type": AccountType.ASSET},
    {"code": "1405", "name": "库存商品", "type": AccountType.ASSET},
    # 负债类
    {"code": "2202", "name": "应付账款", "type": AccountType.LIABILITY},
    {"code": "2211", "name": "应付职工薪酬", "type": AccountType.LIABILITY},
    {"code": "2221", "name": "应交税费", "type": AccountType.LIABILITY},
    {"code": "2241", "name": "预收账款", "type": AccountType.LIABILITY},
    # 所有者权益类
    {"code": "4001", "name": "实收资本", "type": AccountType.EQUITY},
    {"code": "4002", "name": "资本公积", "type": AccountType.EQUITY},
    {"code": "4103", "name": "本年利润", "type": AccountType.EQUITY},
    # 收入类
    {"code": "6001", "name": "主营业务收入", "type": AccountType.REVENUE},
    {"code": "6051", "name": "其他业务收入", "type": AccountType.REVENUE},
    # 成本类
    {"code": "6401", "name": "主营业务成本", "type": AccountType.COST},
    # 费用类
    {"code": "6601", "name": "销售费用", "type": AccountType.EXPENSE},
    {"code": "6602", "name": "管理费用", "type": AccountType.EXPENSE},
    {"code": "6603", "name": "财务费用", "type": AccountType.EXPENSE},
]


def main() -> None:
    """
    初始化标准会计科目。

    逻辑说明：
    - 先确保表存在
    - 再逐条检查 code 是否已存在
    - 已存在则跳过，不存在则插入
    """
    # 确保数据库中的 accounts 表已经创建。
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    inserted_count = 0
    skipped_count = 0

    try:
        for item in STANDARD_ACCOUNTS:
            existing_account = db.scalar(
                select(Account).where(Account.code == item["code"])
            )

            # 如果科目编码已存在，则跳过，避免重复插入。
            if existing_account is not None:
                skipped_count += 1
                print(f"跳过已存在科目: {item['code']} {item['name']}")
                continue

            account = Account(
                code=item["code"],
                name=item["name"],
                type=item["type"],
                parent_id=None,
                is_active=True,
            )
            db.add(account)
            inserted_count += 1
            print(f"插入科目: {item['code']} {item['name']}")

        db.commit()
        print(
            f"初始化完成，共插入 {inserted_count} 条，跳过 {skipped_count} 条已存在记录。"
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
