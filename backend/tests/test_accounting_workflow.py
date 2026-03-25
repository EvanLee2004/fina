"""
会计严谨性相关测试。
"""

from __future__ import annotations

import unittest
from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from core.database import Base
from models.account import Account, AccountType
from models.accounting_policy import AccountingStandard
from schemas.policy import AccountingPolicyUpdate
from schemas.voucher import VoucherCreate, VoucherEntryCreate
from services.accounting.policy_service import upsert_accounting_policy
from services.accounting.voucher_service import create_voucher


class AccountingWorkflowTests(unittest.TestCase):
    """
    验证会计政策和凭证校验链路。
    """

    def setUp(self) -> None:
        engine = create_engine("sqlite:///:memory:", future=True)
        Base.metadata.create_all(bind=engine)
        self.session_factory = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)
        self.db = self.session_factory()

        self.cash_account = Account(code="1002", name="银行存款", type=AccountType.ASSET)
        self.revenue_account = Account(code="6001", name="主营业务收入", type=AccountType.REVENUE)
        self.db.add_all([self.cash_account, self.revenue_account])
        self.db.commit()
        self.db.refresh(self.cash_account)
        self.db.refresh(self.revenue_account)

    def tearDown(self) -> None:
        self.db.close()

    def test_accounting_standard_cannot_switch_when_locked(self) -> None:
        first_policy = upsert_accounting_policy(
            self.db,
            AccountingPolicyUpdate(
                company_name="测试公司",
                accounting_standard=AccountingStandard.SMALL_BUSINESS,
                standard_locked=True,
            ),
        )
        self.assertEqual(first_policy.accounting_standard, AccountingStandard.SMALL_BUSINESS)

        with self.assertRaises(ValueError):
            upsert_accounting_policy(
                self.db,
                AccountingPolicyUpdate(accounting_standard=AccountingStandard.ENTERPRISE),
            )

    def test_create_voucher_rejects_two_sided_entry(self) -> None:
        with self.assertRaises(ValueError):
            create_voucher(
                self.db,
                VoucherCreate(
                    date=date(2026, 3, 25),
                    memo="错误分录",
                    entries=[
                        VoucherEntryCreate(
                            account_id=self.cash_account.id,
                            debit=Decimal("100.00"),
                            credit=Decimal("100.00"),
                        ),
                        VoucherEntryCreate(
                            account_id=self.revenue_account.id,
                            debit=Decimal("0.00"),
                            credit=Decimal("100.00"),
                        ),
                    ],
                ),
            )

    def test_create_voucher_accepts_balanced_entries(self) -> None:
        voucher = create_voucher(
            self.db,
            VoucherCreate(
                date=date(2026, 3, 25),
                memo="正常分录",
                entries=[
                    VoucherEntryCreate(
                        account_id=self.cash_account.id,
                        debit=Decimal("100.00"),
                        credit=Decimal("0.00"),
                    ),
                    VoucherEntryCreate(
                        account_id=self.revenue_account.id,
                        debit=Decimal("0.00"),
                        credit=Decimal("100.00"),
                    ),
                ],
            ),
        )
        self.assertEqual(voucher.memo, "正常分录")
        self.assertEqual(len(voucher.entries), 2)
