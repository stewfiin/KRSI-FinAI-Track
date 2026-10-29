from decimal import Decimal
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_session
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.enums import CategoryType, WalletType
from app.models.category import Category
from app.models.user import User
from app.models.wallet import Wallet
from app.models.transaction import Transaction
from app.models.budget import Budget
from app.models.fixed_expense import FixedExpense
from app.models.wishlist import Wishlist
from app.models.income_stream import IncomeStream
from app.models.financial_plan import FinancialPlan
from app.models.ai_chat_log import AIChatLog
from app.schemas.auth import (
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)

router = APIRouter()

# Definisi template kategori dasar untuk user baru
DEFAULT_CATEGORIES = [
    # Kategori Pengeluaran (Expense)
    {"name": "Makanan & Minuman", "type": CategoryType.EXPENSE, "icon": "utensils", "color": "#EF4444"},
    {"name": "Transportasi", "type": CategoryType.EXPENSE, "icon": "car", "color": "#F59E0B"},
    {"name": "Belanja", "type": CategoryType.EXPENSE, "icon": "shopping-bag", "color": "#3B82F6"},
    {"name": "Tagihan & Utilitas", "type": CategoryType.EXPENSE, "icon": "file-text", "color": "#8B5CF6"},
    {"name": "Hiburan", "type": CategoryType.EXPENSE, "icon": "film", "color": "#EC4899"},
    {"name": "Kesehatan", "type": CategoryType.EXPENSE, "icon": "heart-pulse", "color": "#10B981"},
    # Kategori Pemasukan (Income)
    {"name": "Gaji", "type": CategoryType.INCOME, "icon": "briefcase", "color": "#10B981"},
    {"name": "Bonus & Freelance", "type": CategoryType.INCOME, "icon": "gift", "color": "#06B6D4"},
    {"name": "Uang Saku", "type": CategoryType.INCOME, "icon": "coins", "color": "#84CC16"},
    {"name": "Investasi", "type": CategoryType.INCOME, "icon": "trending-up", "color": "#14B8A6"},
    {"name": "Lain-lain", "type": CategoryType.INCOME, "icon": "plus-circle", "color": "#6B7280"},
]


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrasi User Baru",
    description="Mendaftarkan pengguna baru, otomatis membuat 1 dompet default 'Tunai', dan menginisialisasi 10 kategori dasar.",
)
async def register(
    payload: UserRegisterRequest,
    session: AsyncSession = Depends(get_session),
):
    # 1. Cek apakah email sudah terdaftar
    statement = select(User).where(User.email == payload.email.lower().strip())
    result = await session.exec(statement)
    existing_user = result.first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Alamat email sudah terdaftar. Silakan login atau gunakan email lain.",
        )

    # 2. Buat entitas User baru dengan hashed password
    hashed_pwd = get_password_hash(payload.password)
    new_user = User(
        name=payload.name.strip(),
        email=payload.email.lower().strip(),
        password_hash=hashed_pwd,
        default_currency=payload.default_currency or "IDR",
    )
    session.add(new_user)
    await session.flush()  # Dapatkan new_user.id sebelum membuat dompet & kategori

    # 3. Otomatis buatkan 1 Dompet default 'Tunai'
    default_wallet = Wallet(
        user_id=new_user.id,
        name="Tunai",
        type=WalletType.CASH,
        balance=Decimal("0.00"),
    )
    session.add(default_wallet)

    # 4. Otomatis buatkan kumpulan kategori dasar
    for cat in DEFAULT_CATEGORIES:
        category_obj = Category(
            user_id=new_user.id,
            name=cat["name"],
            type=cat["type"],
            icon=cat["icon"],
            color=cat["color"],
        )
        session.add(category_obj)

    # 5. Commit transaksi secara atomic
    await session.commit()
    await session.refresh(new_user)

    # 6. Terbitkan Access Token JWT
    access_token = create_access_token(subject=str(new_user.id))
    expires_in_seconds = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=expires_in_seconds,
        user=UserResponse.model_validate(new_user),
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login Pengguna",
    description="Autentikasi dengan email dan password, menghasilkan Access Token JWT.",
)
async def login(
    payload: UserLoginRequest,
    session: AsyncSession = Depends(get_session),
):
    # 1. Cari user berdasarkan email
    statement = select(User).where(User.email == payload.email.lower().strip())
    result = await session.exec(statement)
    user = result.first()

    # 2. Validasi user dan password
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email atau password yang Anda masukkan salah.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 3. Terbitkan Access Token JWT
    access_token = create_access_token(subject=str(user.id))
    expires_in_seconds = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=expires_in_seconds,
        user=UserResponse.model_validate(user),
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Profil Pengguna Saat Ini",
    description="Mengambil data profil pengguna yang sedang login berdasarkan Access Token JWT.",
)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
):
    return UserResponse.model_validate(current_user)


@router.post(
    "/reset-data",
    summary="Reset Seluruh Data Keuangan Pengguna",
    description="Menghapus seluruh transaksi, dompet, anggaran, tagihan pasti, wishlist, aliran pendapatan, dan chat AI. Mengembalikan akun ke kondisi bersih seperti akun baru dengan 1 dompet Tunai default.",
)
async def reset_user_financial_data(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    # 1. Hapus seluruh data transaksi
    await session.exec(delete(Transaction).where(Transaction.user_id == current_user.id))
    # 2. Hapus seluruh data anggaran (budgets)
    await session.exec(delete(Budget).where(Budget.user_id == current_user.id))
    # 3. Hapus seluruh tagihan pasti (fixed_expenses)
    await session.exec(delete(FixedExpense).where(FixedExpense.user_id == current_user.id))
    # 4. Hapus seluruh wishlist belanja
    await session.exec(delete(Wishlist).where(Wishlist.user_id == current_user.id))
    # 5. Hapus seluruh multi-stream income
    await session.exec(delete(IncomeStream).where(IncomeStream.user_id == current_user.id))
    # 6. Hapus seluruh chat log AI
    await session.exec(delete(AIChatLog).where(AIChatLog.user_id == current_user.id))
    # 7. Hapus seluruh rencana keuangan blueprint
    await session.exec(delete(FinancialPlan).where(FinancialPlan.user_id == current_user.id))
    # 8. Hapus seluruh dompet
    await session.exec(delete(Wallet).where(Wallet.user_id == current_user.id))

    # 9. Buatkan 1 Dompet default 'Tunai' dengan saldo 0 (persis seperti saat akun baru dibuat)
    default_wallet = Wallet(
        user_id=current_user.id,
        name="Tunai",
        type=WalletType.CASH,
        balance=Decimal("0.00"),
    )
    session.add(default_wallet)

    # 10. Pastikan kategori dasar tersedia
    cat_query = select(Category).where(Category.user_id == current_user.id)
    existing_cats = (await session.exec(cat_query)).all()
    if not existing_cats:
        for cat in DEFAULT_CATEGORIES:
            session.add(
                Category(
                    user_id=current_user.id,
                    name=cat["name"],
                    type=cat["type"],
                    icon=cat["icon"],
                    color=cat["color"],
                )
            )

    await session.commit()
    return {"status": "success", "message": "Seluruh data keuangan berhasil di-reset menjadi seperti akun baru."}

