"""
文件导出相关路由。

这里提供两类正式交付物：
1. Excel 财务包
2. Word 财务报告

它们都是智能体可调用的稳定工具，而不是临时脚本。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.auth import verify_token
from core.database import get_db
from core.memory_database import get_memory_db
from schemas.export import CombinedExportResponse, ExportFileResponse, ExportRequest
from services.reporting.export_excel_service import export_financial_excel
from services.reporting.export_word_service import export_financial_word_report

router = APIRouter(
    prefix="/api/admin/exports",
    tags=["Exports"],
    dependencies=[Depends(verify_token)],
)


@router.post("/excel", response_model=ExportFileResponse)
def export_excel(
    payload: ExportRequest,
    db: Session = Depends(get_db),
    memory_db: Session = Depends(get_memory_db),
) -> ExportFileResponse:
    """
    导出指定期间的 Excel 财务包。
    """
    try:
        return export_financial_excel(db, memory_db, payload.period, model=payload.model)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post("/word", response_model=ExportFileResponse)
def export_word(
    payload: ExportRequest,
    db: Session = Depends(get_db),
    memory_db: Session = Depends(get_memory_db),
) -> ExportFileResponse:
    """
    导出指定期间的 Word 财务报告。
    """
    try:
        return export_financial_word_report(db, memory_db, payload.period, model=payload.model)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post("/all", response_model=CombinedExportResponse)
def export_all(
    payload: ExportRequest,
    db: Session = Depends(get_db),
    memory_db: Session = Depends(get_memory_db),
) -> CombinedExportResponse:
    """
    一次性导出 Excel 和 Word 两个交付物。
    """
    try:
        excel_file = export_financial_excel(db, memory_db, payload.period, model=payload.model)
        word_file = export_financial_word_report(db, memory_db, payload.period, model=payload.model)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return CombinedExportResponse(period=payload.period, files=[excel_file, word_file])
