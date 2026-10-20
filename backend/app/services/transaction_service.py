import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import extract, func
from sqlmodel import and_, desc, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.budget import Budget
from app.models.category import Category
from app.models.enums import CategoryType, TransactionSource, TransactionType
from app.models.transaction import Transaction
from app.models.wallet import Wallet
from app.schemas.budget import BudgetAlert
from app.schemas.dashboard import (
    BudgetSummaryItem,
    CategoryExpenseBreakdown,
    DailyCashflow,
    DashboardSummaryResponse,
)
from app.schemas.transaction import (
    TransactionCreate,
    TransactionResponse,
    TransactionResultResponse,
    TransactionUpdate,
)
from app.schemas.wallet import WalletResponse


class TransactionService:
    @staticmethod
    async def create_transaction(
        session: AsyncSession,
        user_id: uuid.UUID,
        payload: TransactionCreate,
    ) -> TransactionResultResponse:
        """
        Membuat transaksi baru secara atomic:
        1. Validasi kepemilikan dompet & kategori.
        2. Perbarui saldo dompet (Increment / Decrement).
        3. Simpan baris transaksi ke tabel transactions.
        4. Cek batas anggaran (Budget Monitor) untuk bulan berjalan jika transaksi adalah pengeluaran.
        5. Lakukan atomic commit.
        """
        # 1. Validasi Dompet Sumber
        wallet = await session.get(Wallet, payload.wallet_id)
        if not wallet or wallet.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dompet sumber tidak ditemukan atau bukan milik akun Anda.",
            )

        # 2. Validasi Kategori (Kategori milik user ATAU kategori default sistem user_id IS NULL)
        category = await session.get(Category, payload.category_id)
        if not category or (category.user_id is not None and category.user_id != user_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Kategori tidak ditemukan atau tidak dapat diakses.",
            )

        # 3. Penyesuaian Saldo Dompet secara Atomic
        tx_date = payload.transaction_date or date.today()
        dest_wallet: Optional[Wallet] = None

        if payload.type == TransactionType.EXPENSE:
            wallet.balance -= payload.amount
        elif payload.type == TransactionType.INCOME:
            wallet.balance += payload.amount
        elif payload.type == TransactionType.TRANSFER:
            if not payload.destination_wallet_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="ID dompet tujuan wajib disertakan untuk transaksi transfer.",
                )
            if payload.destination_wallet_id == payload.wallet_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Dompet tujuan tidak boleh sama dengan dompet asal.",
                )
            dest_wallet = await session.get(Wallet, payload.destination_wallet_id)
            if not dest_wallet or dest_wallet.user_id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Dompet tujuan tidak ditemukan atau bukan milik akun Anda.",
                )
            wallet.balance -= payload.amount
            dest_wallet.balance += payload.amount
            session.add(dest_wallet)

        session.add(wallet)

        # 4. Buat entitas transaksi
        tx = Transaction(
            user_id=user_id,
            wallet_id=payload.wallet_id,
            category_id=payload.category_id,
            amount=payload.amount,
            type=payload.type,
            description=payload.description,
            transaction_date=tx_date,
            source=payload.source,
        )
        session.add(tx)

        # Flush ke database agar entitas baru terhitung dalam kueri agregasi anggaran berikutnya
        await session.flush()

        # 5. Budget Monitor Service (Pemeriksaan pemakaian batas anggaran)
        budget_alert: Optional[BudgetAlert] = None
        if payload.type == TransactionType.EXPENSE:
            budget_alert = await TransactionService._check_budget_threshold(
                session=session,
                user_id=user_id,
                category_id=payload.category_id,
                category_name=category.name,
                tx_date=tx_date,
            )

        # 6. Atomic Commit
        await session.commit()
        await session.refresh(tx)

        # 7. Siapkan respons dengan metadata
        tx_response = TransactionResponse(
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
            wallet_name=wallet.name,
            category_name=category.name,
            category_color=category.color,
            category_icon=category.icon,
        )

        return TransactionResultResponse(
            transaction=tx_response,
            budget_alert=budget_alert,
        )

    @staticmethod
    async def _check_budget_threshold(
        session: AsyncSession,
        user_id: uuid.UUID,
        category_id: uuid.UUID,
        category_name: str,
        tx_date: date,
    ) -> Optional[BudgetAlert]:
        """Cek apakah total pengeluaran kategori di bulan berjalan mencapai ambang batas >=80% atau >=100%."""
        month = tx_date.month
        year = tx_date.year

        # Cari budget aktif untuk kategori di bulan & tahun ini
        budget_query = select(Budget).where(
            Budget.user_id == user_id,
            Budget.category_id == category_id,
            Budget.month == month,
            Budget.year == year,
        )
        budget_res = await session.exec(budget_query)
        budget = budget_res.first()

        if not budget or budget.amount_limit <= 0:
            return None

        # Hitung total pengeluaran kategori bulan ini
        spent_query = select(func.coalesce(func.sum(Transaction.amount), Decimal("0.00"))).where(
            Transaction.user_id == user_id,
            Transaction.category_id == category_id,
            Transaction.type == TransactionType.EXPENSE,
            extract("month", Transaction.transaction_date) == month,
            extract("year", Transaction.transaction_date) == year,
        )
        spent_res = await session.exec(spent_query)
        total_spent: Decimal = spent_res.one()

        percentage = float((total_spent / budget.amount_limit) * Decimal("100.0"))

        if percentage >= 100.0:
            return BudgetAlert(
                level="danger",
                category_name=category_name,
                amount_limit=budget.amount_limit,
                spent_amount=total_spent,
                percentage_used=round(percentage, 1),
                message=f"Peringatan! Pengeluaran kategori '{category_name}' telah melampaui batas anggaran ({round(percentage, 1)}%). Batas: Rp{budget.amount_limit:,.0f}, Terpakai: Rp{total_spent:,.0f}.",
            )
        elif percentage >= 80.0:
            return BudgetAlert(
                level="warning",
                category_name=category_name,
                amount_limit=budget.amount_limit,
                spent_amount=total_spent,
                percentage_used=round(percentage, 1),
                message=f"Perhatian! Pengeluaran kategori '{category_name}' telah mencapai {round(percentage, 1)}% dari batas anggaran bulanan.",
            )

        return None

    @staticmethod
    async def get_transactions(
        session: AsyncSession,
        user_id: uuid.UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        wallet_id: Optional[uuid.UUID] = None,
        category_id: Optional[uuid.UUID] = None,
        tx_type: Optional[TransactionType] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[TransactionResponse]:
        """Ambil riwayat transaksi dengan filter lengkap dan relasi nama dompet/kategori."""
        query = (
            select(Transaction, Wallet.name.label("wallet_name"), Category.name.label("category_name"), Category.color.label("category_color"), Category.icon.label("category_icon"))
            .join(Wallet, Transaction.wallet_id == Wallet.id)
            .join(Category, Transaction.category_id == Category.id)
            .where(Transaction.user_id == user_id)
        )

        if start_date:
            query = query.where(Transaction.transaction_date >= start_date)
        if end_date:
            query = query.where(Transaction.transaction_date <= end_date)
        if wallet_id:
            query = query.where(Transaction.wallet_id == wallet_id)
        if category_id:
            query = query.where(Transaction.category_id == category_id)
        if tx_type:
            query = query.where(Transaction.type == tx_type)

        query = query.order_by(desc(Transaction.transaction_date), desc(Transaction.created_at)).limit(limit).offset(offset)
        result = await session.exec(query)
        rows = result.all()

        items: List[TransactionResponse] = []
        for row in rows:
            tx, w_name, c_name, c_color, c_icon = row
            items.append(
                TransactionResponse(
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
                    wallet_name=w_name,
                    category_name=c_name,
                    category_color=c_color,
                    category_icon=c_icon,
                )
            )
        return items

    @staticmethod
    async def delete_transaction(
        session: AsyncSession,
        user_id: uuid.UUID,
        transaction_id: uuid.UUID,
    ) -> None:
        """Menghapus transaksi dan membalikkan perubahan saldo dompet secara atomic."""
        tx = await session.get(Transaction, transaction_id)
        if not tx or tx.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transaksi tidak ditemukan atau bukan milik akun Anda.",
            )

        wallet = await session.get(Wallet, tx.wallet_id)
        if wallet:
            # Membalikkan saldo dompet asal
            if tx.type == TransactionType.EXPENSE:
                wallet.balance += tx.amount
            elif tx.type == TransactionType.INCOME:
                wallet.balance -= tx.amount
            elif tx.type == TransactionType.TRANSFER:
                wallet.balance += tx.amount
            session.add(wallet)

        await session.delete(tx)
        await session.commit()

    @staticmethod
    async def update_transaction(
        session: AsyncSession,
        user_id: uuid.UUID,
        transaction_id: uuid.UUID,
        payload: TransactionUpdate,
    ) -> TransactionResponse:
        """Memperbarui transaksi dan menyesuaikan selisih saldo dompet secara atomic."""
        tx = await session.get(Transaction, transaction_id)
        if not tx or tx.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transaksi tidak ditemukan atau bukan milik akun Anda.",
            )

        old_wallet = await session.get(Wallet, tx.wallet_id)
        old_amount = tx.amount
        old_type = tx.type

        # Kembalikan saldo dompet lama terlebih dahulu
        if old_wallet:
            if old_type == TransactionType.EXPENSE:
                old_wallet.balance += old_amount
            elif old_type == TransactionType.INCOME:
                old_wallet.balance -= old_amount
            elif old_type == TransactionType.TRANSFER:
                old_wallet.balance += old_amount
            session.add(old_wallet)

        # Terapkan pembaruan
        if payload.wallet_id is not None:
            new_wallet = await session.get(Wallet, payload.wallet_id)
            if not new_wallet or new_wallet.user_id != user_id:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dompet baru tidak valid.")
            tx.wallet_id = payload.wallet_id
        else:
            new_wallet = old_wallet

        if payload.category_id is not None:
            new_cat = await session.get(Category, payload.category_id)
            if not new_cat or (new_cat.user_id is not None and new_cat.user_id != user_id):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kategori baru tidak valid.")
            tx.category_id = payload.category_id

        if payload.amount is not None:
            tx.amount = payload.amount
        if payload.type is not None:
            tx.type = payload.type
        if payload.description is not None:
            tx.description = payload.description
        if payload.transaction_date is not None:
            tx.transaction_date = payload.transaction_date

        # Terapkan saldo pada dompet (baru/lama)
        if new_wallet:
            if tx.type == TransactionType.EXPENSE:
                new_wallet.balance -= tx.amount
            elif tx.type == TransactionType.INCOME:
                new_wallet.balance += tx.amount
            elif tx.type == TransactionType.TRANSFER:
                new_wallet.balance -= tx.amount
            session.add(new_wallet)

        session.add(tx)
        await session.commit()
        await session.refresh(tx)

        # Ambil metadata nama dompet & kategori
        wallet_obj = await session.get(Wallet, tx.wallet_id)
        cat_obj = await session.get(Category, tx.category_id)

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
            wallet_name=wallet_obj.name if wallet_obj else None,
            category_name=cat_obj.name if cat_obj else None,
            category_color=cat_obj.color if cat_obj else None,
            category_icon=cat_obj.icon if cat_obj else None,
        )

    @staticmethod
    async def get_dashboard_summary(
        session: AsyncSession,
        user_id: uuid.UUID,
    ) -> DashboardSummaryResponse:
        """
        Menghasilkan rekapitulasi data Dashboard terpadu:
        - Total saldo gabungan seluruh dompet
        - Daftar dompet aktif
        - Pemasukan, Pengeluaran, & Net Cashflow bulan ini
        - Komposisi pengeluaran per kategori (Donut Chart)
        - Arus kas 7 hari terakhir (Bar Chart)
        - 5 transaksi terkini
        - Status progress bar anggaran per kategori bulan ini
        """
        today = date.today()
        current_month = today.month
        current_year = today.year

        # 1. Total Saldo & Daftar Dompet
        wallets_query = select(Wallet).where(Wallet.user_id == user_id).order_by(desc(Wallet.created_at))
        wallets_res = await session.exec(wallets_query)
        wallets = wallets_res.all()

        total_balance = sum((w.balance for w in wallets), Decimal("0.00"))
        wallet_responses = [WalletResponse.model_validate(w) for w in wallets]

        # 2. Pemasukan & Pengeluaran Bulan Berjalan
        income_query = select(func.coalesce(func.sum(Transaction.amount), Decimal("0.00"))).where(
            Transaction.user_id == user_id,
            Transaction.type == TransactionType.INCOME,
            extract("month", Transaction.transaction_date) == current_month,
            extract("year", Transaction.transaction_date) == current_year,
        )
        monthly_income: Decimal = (await session.exec(income_query)).one()

        expense_query = select(func.coalesce(func.sum(Transaction.amount), Decimal("0.00"))).where(
            Transaction.user_id == user_id,
            Transaction.type == TransactionType.EXPENSE,
            extract("month", Transaction.transaction_date) == current_month,
            extract("year", Transaction.transaction_date) == current_year,
        )
        monthly_expense: Decimal = (await session.exec(expense_query)).one()
        net_cashflow = monthly_income - monthly_expense

        # 3. Komposisi Pengeluaran per Kategori Bulan Ini (Donut Chart)
        cat_expense_query = (
            select(
                Category.id,
                Category.name,
                Category.color,
                Category.icon,
                func.coalesce(func.sum(Transaction.amount), Decimal("0.00")).label("cat_total"),
            )
            .join(Transaction, Category.id == Transaction.category_id)
            .where(
                Transaction.user_id == user_id,
                Transaction.type == TransactionType.EXPENSE,
                extract("month", Transaction.transaction_date) == current_month,
                extract("year", Transaction.transaction_date) == current_year,
            )
            .group_by(Category.id, Category.name, Category.color, Category.icon)
            .order_by(desc("cat_total"))
        )
        cat_expense_rows = (await session.exec(cat_expense_query)).all()

        category_breakdown: List[CategoryExpenseBreakdown] = []
        for cat_id, cat_name, cat_color, cat_icon, cat_total in cat_expense_rows:
            pct = float((cat_total / monthly_expense) * Decimal("100.0")) if monthly_expense > 0 else 0.0
            category_breakdown.append(
                CategoryExpenseBreakdown(
                    category_id=str(cat_id),
                    category_name=cat_name,
                    category_color=cat_color,
                    category_icon=cat_icon,
                    total_amount=cat_total,
                    percentage=round(pct, 1),
                )
            )

        # 4. Tren Arus Kas 7 Hari Terakhir (Bar Chart)
        day_names = ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"]
        recent_7_days: List[DailyCashflow] = []
        seven_days_ago = today - timedelta(days=6)

        daily_query = (
            select(
                Transaction.transaction_date,
                Transaction.type,
                func.coalesce(func.sum(Transaction.amount), Decimal("0.00")).label("day_total"),
            )
            .where(
                Transaction.user_id == user_id,
                Transaction.transaction_date >= seven_days_ago,
                Transaction.transaction_date <= today,
                Transaction.type.in_([TransactionType.INCOME, TransactionType.EXPENSE]),
            )
            .group_by(Transaction.transaction_date, Transaction.type)
        )
        daily_rows = (await session.exec(daily_query)).all()

        # Mapping data per tanggal
        daily_map = {}
        for d in range(7):
            curr_d = seven_days_ago + timedelta(days=d)
            daily_map[curr_d] = {"income": Decimal("0.00"), "expense": Decimal("0.00")}

        for tx_d, tx_t, total in daily_rows:
            if tx_d in daily_map:
                if tx_t == TransactionType.INCOME:
                    daily_map[tx_d]["income"] = total
                elif tx_t == TransactionType.EXPENSE:
                    daily_map[tx_d]["expense"] = total

        for curr_d, vals in daily_map.items():
            recent_7_days.append(
                DailyCashflow(
                    date=curr_d.strftime("%Y-%m-%d"),
                    day_name=day_names[curr_d.weekday()],
                    income=vals["income"],
                    expense=vals["expense"],
                )
            )

        # 5. 5 Transaksi Terakhir
        recent_transactions = await TransactionService.get_transactions(
            session=session,
            user_id=user_id,
            limit=5,
            offset=0,
        )

        # 6. Status Anggaran per Kategori Bulan Ini
        budgets_query = (
            select(Budget, Category.name.label("category_name"), Category.color.label("category_color"))
            .join(Category, Budget.category_id == Category.id)
            .where(
                Budget.user_id == user_id,
                Budget.month == current_month,
                Budget.year == current_year,
            )
        )
        budgets_rows = (await session.exec(budgets_query)).all()

        budget_statuses: List[BudgetSummaryItem] = []
        for b_obj, b_cat_name, b_cat_color in budgets_rows:
            # Cari pengeluaran kategori ini di bulan ini
            cat_spent = next((item.total_amount for item in category_breakdown if item.category_id == str(b_obj.category_id)), Decimal("0.00"))
            b_pct = float((cat_spent / b_obj.amount_limit) * Decimal("100.0")) if b_obj.amount_limit > 0 else 0.0

            if b_pct >= 100.0:
                b_status = "overbudget"
            elif b_pct >= 80.0:
                b_status = "waspada"
            else:
                b_status = "aman"

            budget_statuses.append(
                BudgetSummaryItem(
                    category_id=str(b_obj.category_id),
                    category_name=b_cat_name,
                    category_color=b_cat_color,
                    amount_limit=b_obj.amount_limit,
                    spent_amount=cat_spent,
                    percentage_used=round(b_pct, 1),
                    status=b_status,
                )
            )

        return DashboardSummaryResponse(
            total_balance=total_balance,
            wallets=wallet_responses,
            monthly_income=monthly_income,
            monthly_expense=monthly_expense,
            net_cashflow=net_cashflow,
            category_breakdown=category_breakdown,
            recent_7_days_cashflow=recent_7_days,
            recent_transactions=recent_transactions,
            budget_statuses=budget_statuses,
        )
