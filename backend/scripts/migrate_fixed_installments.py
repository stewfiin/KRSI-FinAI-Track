import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from app.core.database import engine
import app.models  # noqa: F401


async def run_migration():
    print("🚀 Starting Migration: Fixed Expense Installments...")

    async with engine.begin() as conn:
        print("-> Altering fixed_expenses table (adding installment columns)...")
        await conn.execute(text("""
            ALTER TABLE fixed_expenses
            ADD COLUMN IF NOT EXISTS principal_amount NUMERIC(15, 2) NULL;
        """))
        await conn.execute(text("""
            ALTER TABLE fixed_expenses
            ADD COLUMN IF NOT EXISTS interest_type VARCHAR(20) NULL;
        """))
        await conn.execute(text("""
            ALTER TABLE fixed_expenses
            ADD COLUMN IF NOT EXISTS interest_rate NUMERIC(7, 4) NULL;
        """))
        await conn.execute(text("""
            ALTER TABLE fixed_expenses
            ADD COLUMN IF NOT EXISTS interest_rate_period VARCHAR(20) NULL;
        """))
        await conn.execute(text("""
            ALTER TABLE fixed_expenses
            ADD COLUMN IF NOT EXISTS total_tenor INTEGER NULL;
        """))
        await conn.execute(text("""
            ALTER TABLE fixed_expenses
            ADD COLUMN IF NOT EXISTS paid_installments INTEGER NOT NULL DEFAULT 0;
        """))

    print("✅ Migration Fixed Expense Installments completed successfully!")


if __name__ == "__main__":
    asyncio.run(run_migration())
