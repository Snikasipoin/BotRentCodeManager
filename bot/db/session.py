from __future__ import annotations

from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from bot.config import get_settings

_settings = get_settings()
_engine = create_async_engine(_settings.database_url, future=True, echo=False)
_session_factory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


def get_engine():
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    return _session_factory


@asynccontextmanager
async def session_scope() -> AsyncSession:
    session = _session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()