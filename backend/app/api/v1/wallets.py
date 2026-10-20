import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select, desc
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_session
from app.models.user import User
from app.models.wallet import Wallet
from app.schemas.wallet import WalletCreate, WalletResponse, WalletUpdate

router = APIRouter()


@router.get("", response_model=List[WalletResponse], summary="Daftar Dompet Pengguna")
async def list_wallets(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    query = select(Wallet).where(Wallet.user_id == current_user.id).order_by(desc(Wallet.created_at))
    result = await session.exec(query)
    return result.all()


@router.post("", response_model=WalletResponse, status_code=status.HTTP_201_CREATED, summary="Tambah Dompet Baru")
async def create_wallet(
    payload: WalletCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    new_wallet = Wallet(
        user_id=current_user.id,
        name=payload.name.strip(),
        type=payload.type,
        balance=payload.balance,
    )
    session.add(new_wallet)
    await session.commit()
    await session.refresh(new_wallet)
    return new_wallet


@router.get("/{wallet_id}", response_model=WalletResponse, summary="Detail Dompet")
async def get_wallet(
    wallet_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    wallet = await session.get(Wallet, wallet_id)
    if not wallet or wallet.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dompet tidak ditemukan atau bukan milik akun Anda.",
        )
    return wallet


@router.put("/{wallet_id}", response_model=WalletResponse, summary="Ubah Data Dompet")
async def update_wallet(
    wallet_id: uuid.UUID,
    payload: WalletUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    wallet = await session.get(Wallet, wallet_id)
    if not wallet or wallet.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dompet tidak ditemukan atau bukan milik akun Anda.",
        )

    if payload.name is not None:
        wallet.name = payload.name.strip()
    if payload.type is not None:
        wallet.type = payload.type
    if payload.balance is not None:
        wallet.balance = payload.balance

    session.add(wallet)
    await session.commit()
    await session.refresh(wallet)
    return wallet


@router.delete("/{wallet_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Hapus Dompet")
async def delete_wallet(
    wallet_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    wallet = await session.get(Wallet, wallet_id)
    if not wallet or wallet.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dompet tidak ditemukan atau bukan milik akun Anda.",
        )

    await session.delete(wallet)
    await session.commit()
    return None

