from typing import AsyncGenerator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import SQLModel

from app.core.config import settings

# Engine database asynchronous menggunakan asyncpg
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
    pool_pre_ping=True,
)

# Async session factory
async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency injection FastAPI untuk menyediakan database session async."""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """Inisialisasi tabel dan pastikan kolom tambahan terbaru tersedia."""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
        if conn.dialect.name == "postgresql":
            for stmt in (
                "ALTER TABLE fixed_expenses ADD COLUMN IF NOT EXISTS principal_amount NUMERIC(15, 2) NULL;",
                "ALTER TABLE fixed_expenses ADD COLUMN IF NOT EXISTS interest_type VARCHAR(20) NULL;",
                "ALTER TABLE fixed_expenses ADD COLUMN IF NOT EXISTS interest_rate NUMERIC(7, 4) NULL;",
                "ALTER TABLE fixed_expenses ADD COLUMN IF NOT EXISTS interest_rate_period VARCHAR(20) NULL;",
                "ALTER TABLE fixed_expenses ADD COLUMN IF NOT EXISTS total_tenor INTEGER NULL;",
                "ALTER TABLE fixed_expenses ADD COLUMN IF NOT EXISTS paid_installments INTEGER NOT NULL DEFAULT 0;",
            ):
                await conn.execute(text(stmt))

