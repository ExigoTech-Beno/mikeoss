"""
asyncpg connection pool for Azure PostgreSQL Flexible Server.
Replaces the Supabase JS client used throughout the Express backend.
"""

import asyncpg
from app.config import settings

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            dsn=settings.postgres_dsn,
            min_size=2,
            max_size=10,
            ssl="require",
        )
    return _pool


async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
