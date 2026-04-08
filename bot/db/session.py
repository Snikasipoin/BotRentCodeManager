from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlparse, unquote

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from bot.config import get_settings


def _ensure_sqlite_directory(database_url: str) -> None:
    if not database_url.startswith("sqlite+aiosqlite:///"):
        return
    parsed = urlparse(database_url.replace("sqlite+aiosqlite:///", "file:///", 1))
    path = unquote(parsed.path)
    if not path or path == "/:memory:":
        return
    file_path = Path(path.lstrip("/"))
    if file_path.parent:
        file_path.parent.mkdir(parents=True, exist_ok=True)


_settings = get_settings()
_ensure_sqlite_directory(_settings.database_url)
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