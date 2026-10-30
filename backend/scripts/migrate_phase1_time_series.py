import asyncio
import sys
from pathlib import Path

# Tambahkan backend path ke sys.path jika belum ada
sys.path.append(str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from sqlmodel import SQLModel
from app.core.database import engine

# Import semua model agar metadata SQLModel lengkap
import app.models  # noqa: F401
from app.models.planned_transaction import PlannedTransaction  # noqa: F401
from app.models.income_stream import IncomeStream  # noqa: F401
from app.models.fixed_expense import FixedExpense  # noqa: F401


async def run_migration():
    print("🚀 Starting Phase 1 Migration: Time-Series & Cyclical Models...")

    async with engine.begin() as conn:
        # 1. Update tabel income_streams: tambah wallet_id
        print("-> Altering income_streams table (adding wallet_id)...")
        await conn.execute(text("""
            ALTER TABLE income_streams 
            ADD COLUMN IF NOT EXISTS wallet_id UUID REFERENCES wallets(id) ON DELETE SET NULL;
        """))

        # 2. Update tabel fixed_expenses: tambah interval_value & anchor_date
        print("-> Altering fixed_expenses table (adding interval_value, anchor_date)...")
        await conn.execute(text("""
            ALTER TABLE fixed_expenses 
            ADD COLUMN IF NOT EXISTS interval_value INTEGER;
        """))
        await conn.execute(text("""
            ALTER TABLE fixed_expenses 
            ADD COLUMN IF NOT EXISTS anchor_date TIMESTAMPTZ;
        """))

        # 3. Create planned_transactions table if not exists using SQLModel metadata
        print("-> Creating planned_transactions table if not exists...")
        await conn.run_sync(SQLModel.metadata.create_all)

    print("✅ Migration Phase 1 completed successfully!")


if __name__ == "__main__":
    asyncio.run(run_migration())
