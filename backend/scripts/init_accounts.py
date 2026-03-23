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


def _account(code: str, name: str, account_type: AccountType) -> dict[str, object]:
    """
    构造标准科目字典。

    单独抽一个小函数的好处是：
    1. 让下面 66 个一级科目列表更紧凑、更易核对。
    2. 避免每一行都重复写相同的字典键名，降低录入错误概率。
    """
    return {"code": code, "name": name, "type": account_type}


# 预置的标准会计科目。
# 这里按照财政部《小企业会计准则》附录中的一级会计科目录入。
# 由于当前项目的 AccountType 拆成了收入、成本、费用三类，
# 因此官方“损益类”会按实际业务属性映射到 revenue / cost / expense。
STANDARD_ACCOUNTS = [
    # 一、资产类（共 32 个）
    _account("1001", "库存现金", AccountType.ASSET),
    _account("1002", "银行存款", AccountType.ASSET),
    _account("1012", "其他货币资金", AccountType.ASSET),
    _account("1101", "短期投资", AccountType.ASSET),
    _account("1121", "应收票据", AccountType.ASSET),
    _account("1122", "应收账款", AccountType.ASSET),
    _account("1123", "预付账款", AccountType.ASSET),
    _account("1131", "应收股利", AccountType.ASSET),
    _account("1132", "应收利息", AccountType.ASSET),
    _account("1221", "其他应收款", AccountType.ASSET),
    _account("1401", "材料采购", AccountType.ASSET),
    _account("1402", "在途物资", AccountType.ASSET),
    _account("1403", "原材料", AccountType.ASSET),
    _account("1404", "材料成本差异", AccountType.ASSET),
    _account("1405", "库存商品", AccountType.ASSET),
    _account("1407", "商品进销差价", AccountType.ASSET),
    _account("1408", "委托加工物资", AccountType.ASSET),
    _account("1411", "周转材料", AccountType.ASSET),
    _account("1421", "消耗性生物资产", AccountType.ASSET),
    _account("1501", "长期债券投资", AccountType.ASSET),
    _account("1511", "长期股权投资", AccountType.ASSET),
    _account("1601", "固定资产", AccountType.ASSET),
    _account("1602", "累计折旧", AccountType.ASSET),
    _account("1604", "在建工程", AccountType.ASSET),
    _account("1605", "工程物资", AccountType.ASSET),
    _account("1606", "固定资产清理", AccountType.ASSET),
    _account("1621", "生产性生物资产", AccountType.ASSET),
    _account("1622", "生产性生物资产累计折旧", AccountType.ASSET),
    _account("1701", "无形资产", AccountType.ASSET),
    _account("1702", "累计摊销", AccountType.ASSET),
    _account("1801", "长期待摊费用", AccountType.ASSET),
    _account("1901", "待处理财产损溢", AccountType.ASSET),
    # 二、负债类（共 12 个）
    _account("2001", "短期借款", AccountType.LIABILITY),
    _account("2201", "应付票据", AccountType.LIABILITY),
    _account("2202", "应付账款", AccountType.LIABILITY),
    _account("2203", "预收账款", AccountType.LIABILITY),
    _account("2211", "应付职工薪酬", AccountType.LIABILITY),
    _account("2221", "应交税费", AccountType.LIABILITY),
    _account("2231", "应付利息", AccountType.LIABILITY),
    _account("2232", "应付利润", AccountType.LIABILITY),
    _account("2241", "其他应付款", AccountType.LIABILITY),
    _account("2401", "递延收益", AccountType.LIABILITY),
    _account("2501", "长期借款", AccountType.LIABILITY),
    _account("2701", "长期应付款", AccountType.LIABILITY),
    # 三、所有者权益类（共 5 个）
    _account("3001", "实收资本", AccountType.EQUITY),
    _account("3002", "资本公积", AccountType.EQUITY),
    _account("3101", "盈余公积", AccountType.EQUITY),
    _account("3103", "本年利润", AccountType.EQUITY),
    _account("3104", "利润分配", AccountType.EQUITY),
    # 四、成本类（共 5 个）
    _account("4001", "生产成本", AccountType.COST),
    _account("4101", "制造费用", AccountType.COST),
    _account("4301", "研发支出", AccountType.COST),
    _account("4401", "工程施工", AccountType.COST),
    _account("4403", "机械作业", AccountType.COST),
    # 五、损益类（共 12 个）
    # 其中收入和利得映射为 revenue，成本映射为 cost，期间费用和损失映射为 expense。
    _account("5001", "主营业务收入", AccountType.REVENUE),
    _account("5051", "其他业务收入", AccountType.REVENUE),
    _account("5111", "投资收益", AccountType.REVENUE),
    _account("5301", "营业外收入", AccountType.REVENUE),
    _account("5401", "主营业务成本", AccountType.COST),
    _account("5402", "其他业务成本", AccountType.COST),
    _account("5403", "营业税金及附加", AccountType.EXPENSE),
    _account("5601", "销售费用", AccountType.EXPENSE),
    _account("5602", "管理费用", AccountType.EXPENSE),
    _account("5603", "财务费用", AccountType.EXPENSE),
    _account("5711", "营业外支出", AccountType.EXPENSE),
    _account("5801", "所得税费用", AccountType.EXPENSE),
]


# 按财政部附录，一级会计科目应为 66 个。
# 这里做一个启动时断言，防止后续维护时误删或漏录科目。
if len(STANDARD_ACCOUNTS) != 66:
    raise ValueError(f"标准会计科目数量应为 66 个，当前为 {len(STANDARD_ACCOUNTS)} 个。")


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
