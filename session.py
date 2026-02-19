"""
Database engine and session factory.
Supports both sync (for scripts/CLI) and async (for high-throughput ingestion).
"""
from contextlib import asynccontextmanager, contextmanager

from sqlalchemy import create_engine, event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from config.settings import settings
from db.models import Base


# ── Async engine (for scrapers / pipelines) ──────────────────────────────────
async_engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=settings.DB_ECHO,
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# ── Sync engine (for Alembic migrations / admin scripts) ─────────────────────
sync_engine = create_engine(
    settings.DATABASE_URL_SYNC,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    echo=settings.DB_ECHO,
)

SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False,
)


# ── Context managers ──────────────────────────────────────────────────────────

@asynccontextmanager
async def get_async_session() -> AsyncSession:
    """Async session for use in scrapers and pipeline."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@contextmanager
def get_sync_session() -> Session:
    """Sync session for scripts and CLI."""
    with SyncSessionLocal() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


# ── Database initialization ───────────────────────────────────────────────────

async def create_all_tables() -> None:
    """Create all tables. Called on first run."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_all_tables() -> None:
    """Drop all tables. DANGEROUS — use only in dev."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def check_connection() -> bool:
    """Verify DB is reachable."""
    try:
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"DB connection failed: {e}")
        return False
