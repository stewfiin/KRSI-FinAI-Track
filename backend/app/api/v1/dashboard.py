from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_session
from app.models.user import User
from app.schemas.dashboard import DashboardSummaryResponse
from app.services.transaction_service import TransactionService

router = APIRouter()


@router.get(
    "/summary",
    response_model=DashboardSummaryResponse,
    summary="Ringkasan Metrik Dashboard Terpadu",
    description="Mengambil seluruh agregasi data keuangan: total saldo, kartu dompet, arus kas bulan ini, komposisi kategori (Donut), tren 7 hari (Bar), 5 transaksi terkini, dan progres anggaran.",
)
async def get_dashboard_summary(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await TransactionService.get_dashboard_summary(
        session=session,
        user_id=current_user.id,
    )

