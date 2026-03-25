"""
Stripe 自动记账与导出烟测。
"""

from __future__ import annotations

import tempfile
import unittest
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from core.config import settings
from core.database import Base
from models.account import Account, AccountType
from models.accounting_policy import AccountingPolicy, AccountingStandard
from models.integration_event import IntegrationEvent
from schemas.report import (
    AgingBucket,
    ExpenseBreakdownItem,
    FinancialNarrative,
    FinancialObjectiveSummary,
    FinancialReportResponse,
    MetricCard,
)
from services.integrations.stripe_service import process_stripe_event
from services.reporting.export_excel_service import export_financial_excel
from services.reporting.export_word_service import export_financial_word_report


class FakeStripeEvent:
    """
    用于测试的简化 Stripe 事件对象。
    """

    def __init__(self) -> None:
        self.id = "evt_test_001"
        self.type = "payment_intent.succeeded"
        self.data = SimpleNamespace(
            object={
                "id": "pi_test_001",
                "amount_received": 12345,
                "currency": "cny",
                "description": "测试订单付款",
                "customer": "cus_test_001",
                "metadata": {"order_id": "SO-001"},
                "created": int(datetime(2026, 3, 25, tzinfo=timezone.utc).timestamp()),
            }
        )

    def to_dict_recursive(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "data": {"object": self.data.object},
        }


class IntegrationAndExportTests(unittest.TestCase):
    """
    压 Stripe 自动记账和导出链路。
    """

    def setUp(self) -> None:
        engine = create_engine("sqlite:///:memory:", future=True)
        Base.metadata.create_all(bind=engine)
        self.session_factory = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)
        self.db = self.session_factory()

        self.debit_account = Account(code="1002", name="银行存款", type=AccountType.ASSET)
        self.credit_account = Account(code="6001", name="主营业务收入", type=AccountType.REVENUE)
        self.db.add_all([self.debit_account, self.credit_account])
        self.db.commit()
        self.db.refresh(self.debit_account)
        self.db.refresh(self.credit_account)

        policy = AccountingPolicy(
            company_name="测试公司",
            accounting_standard=AccountingStandard.SMALL_BUSINESS,
            standard_locked=True,
            require_manual_confirmation=True,
            stripe_receipt_debit_account_id=self.debit_account.id,
            stripe_receipt_credit_account_id=self.credit_account.id,
        )
        self.db.add(policy)
        self.db.commit()

        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_exports_dir = settings.EXPORTS_DIR
        settings.EXPORTS_DIR = self.temp_dir.name

    def tearDown(self) -> None:
        settings.EXPORTS_DIR = self.original_exports_dir
        self.temp_dir.cleanup()
        self.db.close()

    def test_process_stripe_event_creates_draft_voucher(self) -> None:
        result = process_stripe_event(self.db, FakeStripeEvent())
        self.assertEqual(result["status"], "processed")
        self.assertEqual(result["voucher_status"], "draft")

        saved_event = self.db.scalar(select(IntegrationEvent))
        self.assertIsNotNone(saved_event)
        self.assertEqual(saved_event.provider, "stripe")

    def test_export_services_generate_files(self) -> None:
        summary = FinancialObjectiveSummary(
            voucher_count=2,
            total_revenue=Decimal("120000.00"),
            total_expense=Decimal("75000.00"),
            net_profit=Decimal("45000.00"),
            pending_receivables=Decimal("18000.00"),
            pending_payables=Decimal("9000.00"),
            expense_breakdown=[
                ExpenseBreakdownItem(account_name="管理费用", amount=Decimal("32000.00"))
            ],
            receivable_aging=[AgingBucket(label="未到期", amount=Decimal("18000.00"))],
            payable_aging=[AgingBucket(label="未到期", amount=Decimal("9000.00"))],
        )
        report = FinancialReportResponse(
            period="2026-03",
            metrics=[
                MetricCard(label="收入", value=Decimal("120000.00")),
                MetricCard(label="支出", value=Decimal("75000.00")),
            ],
            objective_summary=summary,
            narrative=FinancialNarrative(
                executive_summary="测试概览",
                analysis="测试分析",
                risks=["测试风险"],
                recommendations=["测试建议"],
            ),
            content="测试报告正文",
        )
        voucher = SimpleNamespace(
            id=1,
            date=date(2026, 3, 15),
            memo="测试凭证",
            status=SimpleNamespace(value="approved"),
            created_by="system",
            created_at=datetime(2026, 3, 15, 9, 30, 0),
            entries=[
                SimpleNamespace(
                    id=11,
                    account=SimpleNamespace(name="主营业务收入"),
                    debit=Decimal("0.00"),
                    credit=Decimal("120000.00"),
                )
            ],
        )
        receivable = SimpleNamespace(
            id=21,
            type=SimpleNamespace(value="receivable"),
            party="测试客户",
            amount=Decimal("18000.00"),
            due_date=date(2026, 3, 28),
            status=SimpleNamespace(value="pending"),
            memo="测试应收",
        )
        objective_data = {"vouchers": [voucher], "receivables": [receivable]}

        excel_file = export_financial_excel(
            db=None,
            memory_db=None,
            period="2026-03",
            report=report,
            objective_data=objective_data,
        )
        word_file = export_financial_word_report(
            db=None,
            memory_db=None,
            period="2026-03",
            report=report,
        )

        self.assertTrue(Path(excel_file.path).exists())
        self.assertTrue(Path(word_file.path).exists())
