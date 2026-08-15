"""
Database Connection & Session Management

Uses SQLAlchemy async engine with AsyncSession.
- get_engine(): creates the async engine (called once at startup)
- get_session(): dependency for FastAPI endpoints (yields a session)
- Base: declarative base class for all ORM models

IMPORTANT: This module is imported by models AND by the FastAPI app.
         The actual engine is created lazily via get_engine().
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from typing import AsyncGenerator

from app.core.config import get_settings


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass


def get_engine():
    """
    Create and return the async SQLAlchemy engine.
    
    The engine is created from the DATABASE_URL in settings.
    pool_size and max_overflow control connection pooling:
    - pool_size=10: maintain 10 connections in the pool
    - max_overflow=20: allow up to 20 additional connections under load
    - pool_pre_ping=True: test connections before use (detect stale connections)
    """
    settings = get_settings()
    return create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DATABASE_ECHO,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
    )


def get_session_factory():
    """
    Create a session factory bound to the async engine.
    Used by get_session() to create per-request sessions.
    """
    engine = get_engine()
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,  # Prevents lazy-loading errors after commit
    )


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides a database session per request.
    
    Usage in an endpoint:
        @router.get("/devices")
        async def list_devices(session: AsyncSession = Depends(get_session)):
            ...
    
    The session is automatically closed when the request ends,
    even if an exception occurs (yield + finally).
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
