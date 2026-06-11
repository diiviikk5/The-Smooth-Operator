"""Async database session management for SQLAlchemy 2.0.

Provides:
- ``async_engine``: The shared async engine instance.
- ``async_session_factory``: Session factory for creating new sessions.
- ``get_db()``: FastAPI dependency that yields an async session with
  automatic commit/rollback semantics.

Usage in FastAPI routes:
    from src.db.session import get_db

    @router.get("/items")
    async def list_items(db: AsyncSession = Depends(get_db)):
        result = await db.execute(select(Item))
        return result.scalars().all()
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.config.settings import get_settings

logger = logging.getLogger(__name__)

# ── Engine & Session Factory ─────────────────────────────────────────────────

_settings = get_settings()

async_engine = create_async_engine(
    _settings.database.url,
    pool_size=_settings.database.pool_size,
    max_overflow=_settings.database.max_overflow,
    echo=_settings.database.echo,
    pool_recycle=_settings.database.pool_recycle,
    pool_pre_ping=_settings.database.pool_pre_ping,
    future=True,
)

async_session_factory = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


# ── FastAPI Dependency ───────────────────────────────────────────────────────


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session for use as a FastAPI dependency.

    The session is automatically committed on success or rolled back
    on exception.  It is always closed when the request finishes.

    Yields:
        An ``AsyncSession`` bound to the shared async engine.

    Raises:
        Exception: Re-raises any exception after rolling back the session.
    """
    session = async_session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        logger.exception("Database session rolled back due to error.")
        raise
    finally:
        await session.close()
