import asyncio
from sqlalchemy import text
from sqlmodel import select, desc
from app.core.database import async_session_maker, engine
from app.models.wallet import Wallet
from app.models.fixed_expense import FixedExpense
from app.models.financial_plan import FinancialPlan
from app.models.income_stream import IncomeStream


async def migrate_and_clean():
    async with engine.begin() as conn:
        await conn.execute(text("ALTER TABLE wallets ADD COLUMN IF NOT EXISTS purpose VARCHAR(30) DEFAULT 'operational';"))
        await conn.execute(text("ALTER TABLE fixed_expenses ADD COLUMN IF NOT EXISTS wallet_id UUID REFERENCES wallets(id) ON DELETE SET NULL;"))
        await conn.execute(text("ALTER TABLE fixed_expenses ADD COLUMN IF NOT EXISTS paid_transaction_id UUID REFERENCES transactions(id) ON DELETE SET NULL;"))
        print("DB Schema altered successfully!")

    async with async_session_maker() as s:
        # Update existing wallet purposes based on name
        wallets = (await s.exec(select(Wallet))).all()
        for w in wallets:
            w_name = w.name.lower()
            if "saving" in w_name or "anniv" in w_name or "tabung" in w_name:
                w.purpose = "savings"
            elif "subscrip" in w_name or "tagihan" in w_name:
                w.purpose = "subscription"
            else:
                w.purpose = "operational"
            s.add(w)
            print(f"Wallet updated: {w.name} -> purpose: {w.purpose}")

        # Clean duplicate financial plans
        user_ids = set(p.user_id for p in (await s.exec(select(FinancialPlan))).all())
        for uid in user_ids:
            all_plans = (await s.exec(select(FinancialPlan).where(FinancialPlan.user_id == uid).order_by(desc(FinancialPlan.created_at)))).all()
            if len(all_plans) > 1:
                for extra in all_plans[1:]:
                    await s.delete(extra)
                print(f"Kept 1 plan for user {uid}, removed {len(all_plans)-1} duplicate plans")

        # Clean dummy fixed expenses that were auto-seeded
        fixed_items = (await s.exec(select(FixedExpense))).all()
        deleted_count = 0
        for f in fixed_items:
            await s.delete(f)
            deleted_count += 1
        print(f"Cleaned {deleted_count} dummy fixed expenses")

        await s.commit()
        print("All migrations and cleanup committed successfully!")


if __name__ == "__main__":
    asyncio.run(migrate_and_clean())
