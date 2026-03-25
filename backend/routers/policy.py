"""
公司会计政策路由。

这组接口用于配置当前公司的会计准则和关键记账口径。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.auth import verify_token
from core.database import get_db
from schemas.policy import AccountingPolicyResponse, AccountingPolicyUpdate
from services.accounting.policy_service import get_accounting_policy, upsert_accounting_policy

router = APIRouter(
    prefix="/api/admin/policy",
    tags=["Accounting Policy"],
    dependencies=[Depends(verify_token)],
)


@router.get("/", response_model=AccountingPolicyResponse | None)
def get_policy(
    db: Session = Depends(get_db),
) -> AccountingPolicyResponse | None:
    """
    获取当前公司会计政策。
    """
    policy = get_accounting_policy(db)
    if policy is None:
        return None
    return AccountingPolicyResponse.model_validate(policy)


@router.put("/", response_model=AccountingPolicyResponse)
def update_policy(
    payload: AccountingPolicyUpdate,
    db: Session = Depends(get_db),
) -> AccountingPolicyResponse:
    """
    更新当前公司会计政策。
    """
    try:
        policy = upsert_accounting_policy(db, payload)
        return AccountingPolicyResponse.model_validate(policy)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
