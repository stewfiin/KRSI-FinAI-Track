import uuid
from decimal import Decimal
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select, desc
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_session
from app.models.enums import WalletType
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
        purpose=payload.purpose or "operational",
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
    if payload.purpose is not None:
        wallet.purpose = payload.purpose
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

    user_wallets_res = await session.exec(
        select(Wallet).where(Wallet.user_id == current_user.id).order_by(Wallet.created_at)
    )
    user_wallets = user_wallets_res.all()
    cash_wallets = [w for w in user_wallets if w.type == WalletType.CASH]

    is_primary_tunai = (
        wallet.type == WalletType.CASH
        and (wallet.name or "").strip().lower() == "tunai"
    )
    is_only_cash = wallet.type == WalletType.CASH and len(cash_wallets) <= 1

    if is_primary_tunai or is_only_cash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dompet Tunai (Cash) utama tidak dapat dihapus.",
        )

    # Pindahkan sisa saldo dompet yang dihapus ke dompet Tunai (Cash)
    target_cash_wallet = next(
        (
            w
            for w in cash_wallets
            if w.id != wallet.id and (w.name or "").strip().lower() == "tunai"
        ),
        None,
    )
    if not target_cash_wallet:
        target_cash_wallet = next((w for w in cash_wallets if w.id != wallet.id), None)

    if not target_cash_wallet:
        target_cash_wallet = Wallet(
            user_id=current_user.id,
            name="Tunai",
            type=WalletType.CASH,
            purpose="operational",
            balance=Decimal("0.00"),
        )
        session.add(target_cash_wallet)
        await session.flush()

    if wallet.balance and wallet.balance != Decimal("0.00"):
        target_cash_wallet.balance = (target_cash_wallet.balance or Decimal("0.00")) + wallet.balance
        session.add(target_cash_wallet)

    await session.delete(wallet)
    await session.commit()
    return None

