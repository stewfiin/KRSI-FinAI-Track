import asyncio
import sys
from pathlib import Path

# Tambahkan backend path ke sys.path jika belum ada
sys.path.append(str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from app.core.database import engine

# Import semua model agar metadata SQLModel lengkap
import app.models  # noqa: F401


async def run_migration():
    print("🚀 Starting Migration: Savings Cycles (to_wallet_id & expense_type)...")

    async with engine.begin() as conn:
        print("-> Altering fixed_expenses table (adding to_wallet_id, expense_type)...")
        await conn.execute(text("""
            ALTER TABLE fixed_expenses 
            ADD COLUMN IF NOT EXISTS to_wallet_id UUID REFERENCES wallets(id) ON DELETE SET NULL;
        """))
        await conn.execute(text("""
            ALTER TABLE fixed_expenses 
            ADD COLUMN IF NOT EXISTS expense_type VARCHAR(20) DEFAULT 'EXPENSE';
        """))

    print("✅ Migration Savings Cycles completed successfully!")


if __name__ == "__main__":
    asyncio.run(run_migration())

