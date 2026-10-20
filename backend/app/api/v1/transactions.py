import uuid
from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_session
from app.models.category import Category
from app.models.enums import TransactionType
from app.models.transaction import Transaction
from app.models.user import User
from app.models.wallet import Wallet
from app.schemas.transaction import (
    TransactionCreate,
    TransactionResponse,
    TransactionResultResponse,
    TransactionUpdate,
)
from app.services.transaction_service import TransactionService

router = APIRouter()


@router.post(
    "",
    response_model=TransactionResultResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Catat Transaksi Baru (Atomic)",
    description="Menyimpan transaksi ke database, memperbarui saldo dompet secara atomic, dan mengecek batas anggaran (Budget Monitor).",
)
async def create_transaction(
    payload: TransactionCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await TransactionService.create_transaction(
        session=session,
        user_id=current_user.id,
        payload=payload,
    )


@router.get(
    "",
    response_model=List[TransactionResponse],
    summary="Daftar Riwayat Transaksi",
    description="Mengambil riwayat transaksi dengan dukungan filter rentang tanggal, dompet, kategori, dan pagination.",
)
async def list_transactions(
    start_date: Optional[date] = Query(None, description="Filter tanggal awal (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Filter tanggal akhir (YYYY-MM-DD)"),
    wallet_id: Optional[uuid.UUID] = Query(None, description="Filter berdasarkan dompet"),
    category_id: Optional[uuid.UUID] = Query(None, description="Filter berdasarkan kategori"),
    type: Optional[TransactionType] = Query(None, description="Filter tipe: income, expense, transfer"),
    limit: int = Query(50, ge=1, le=200, description="Batas jumlah baris data"),
    offset: int = Query(0, ge=0, description="Offset pagination"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await TransactionService.get_transactions(
        session=session,
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date,
        wallet_id=wallet_id,
        category_id=category_id,
        tx_type=type,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{transaction_id}",
    response_model=TransactionResponse,
    summary="Detail Transaksi Tunggal",
)
async def get_transaction(
    transaction_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    tx = await session.get(Transaction, transaction_id)
    if not tx or tx.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaksi tidak ditemukan atau bukan milik akun Anda.",
        )

    wallet = await session.get(Wallet, tx.wallet_id)
    category = await session.get(Category, tx.category_id)

    return TransactionResponse(
        id=tx.id,
        user_id=tx.user_id,
        wallet_id=tx.wallet_id,
        category_id=tx.category_id,
        amount=tx.amount,
        type=tx.type,
        description=tx.description,
        transaction_date=tx.transaction_date,
        source=tx.source,
        created_at=tx.created_at,
        wallet_name=wallet.name if wallet else None,
        category_name=category.name if category else None,
        category_color=category.color if category else None,
        category_icon=category.icon if category else None,
    )


@router.put(
    "/{transaction_id}",
    response_model=TransactionResponse,
    summary="Ubah Transaksi (Atomic Adjustment)",
)
async def update_transaction(
    transaction_id: uuid.UUID,
    payload: TransactionUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await TransactionService.update_transaction(
        session=session,
        user_id=current_user.id,
        transaction_id=transaction_id,
        payload=payload,
    )


@router.delete(
    "/{transaction_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Hapus Transaksi (Atomic Revert)",
)
async def delete_transaction(
    transaction_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await TransactionService.delete_transaction(
        session=session,
        user_id=current_user.id,
        transaction_id=transaction_id,
    )
    return None

