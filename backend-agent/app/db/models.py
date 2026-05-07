"""
Typed query helpers for each table.
Mirrors the Supabase schema in backend/migrations/000_one_shot_schema.sql.
"""

from __future__ import annotations
import uuid
from datetime import datetime
from typing import Any
import asyncpg


# ---------------------------------------------------------------------------
# Users / profiles
# ---------------------------------------------------------------------------

async def get_user_profile(db: asyncpg.Pool, user_id: str) -> dict | None:
    row = await db.fetchrow(
        "SELECT * FROM user_profiles WHERE user_id = $1", user_id
    )
    return dict(row) if row else None


async def upsert_user_profile(db: asyncpg.Pool, user_id: str, email: str) -> dict:
    row = await db.fetchrow(
        """
        INSERT INTO user_profiles (user_id, email)
        VALUES ($1, $2)
        ON CONFLICT (user_id) DO UPDATE SET updated_at = now()
        RETURNING *
        """,
        user_id, email,
    )
    return dict(row)


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------

async def list_projects(db: asyncpg.Pool, user_id: str) -> list[dict]:
    rows = await db.fetch(
        "SELECT * FROM projects WHERE user_id = $1 ORDER BY created_at DESC",
        user_id,
    )
    return [dict(r) for r in rows]


async def create_project(db: asyncpg.Pool, user_id: str, name: str, **kwargs) -> dict:
    row = await db.fetchrow(
        """
        INSERT INTO projects (id, user_id, name, cm_number, visibility)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING *
        """,
        str(uuid.uuid4()), user_id, name,
        kwargs.get("cm_number"), kwargs.get("visibility", "private"),
    )
    return dict(row)


async def get_project(db: asyncpg.Pool, project_id: str) -> dict | None:
    row = await db.fetchrow("SELECT * FROM projects WHERE id = $1", project_id)
    return dict(row) if row else None


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------

async def list_documents(db: asyncpg.Pool, project_id: str) -> list[dict]:
    rows = await db.fetch(
        "SELECT * FROM documents WHERE project_id = $1 ORDER BY created_at DESC",
        project_id,
    )
    return [dict(r) for r in rows]


async def create_document(db: asyncpg.Pool, user_id: str, project_id: str | None,
                          filename: str, file_type: str, storage_path: str) -> dict:
    row = await db.fetchrow(
        """
        INSERT INTO documents (id, user_id, project_id, filename, file_type, storage_path)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING *
        """,
        str(uuid.uuid4()), user_id, project_id, filename, file_type, storage_path,
    )
    return dict(row)


async def get_document(db: asyncpg.Pool, doc_id: str) -> dict | None:
    row = await db.fetchrow("SELECT * FROM documents WHERE id = $1", doc_id)
    return dict(row) if row else None


# ---------------------------------------------------------------------------
# Chats
# ---------------------------------------------------------------------------

async def list_chats(db: asyncpg.Pool, user_id: str) -> list[dict]:
    rows = await db.fetch(
        "SELECT * FROM chats WHERE user_id = $1 ORDER BY created_at DESC",
        user_id,
    )
    return [dict(r) for r in rows]


async def create_chat(db: asyncpg.Pool, user_id: str, project_id: str | None = None) -> dict:
    row = await db.fetchrow(
        """
        INSERT INTO chats (id, user_id, project_id)
        VALUES ($1, $2, $3)
        RETURNING *
        """,
        str(uuid.uuid4()), user_id, project_id,
    )
    return dict(row)


async def list_chat_messages(db: asyncpg.Pool, chat_id: str) -> list[dict]:
    rows = await db.fetch(
        "SELECT * FROM chat_messages WHERE chat_id = $1 ORDER BY created_at ASC",
        chat_id,
    )
    return [dict(r) for r in rows]


async def append_chat_message(db: asyncpg.Pool, chat_id: str, role: str,
                               content: str, model: str | None = None) -> dict:
    row = await db.fetchrow(
        """
        INSERT INTO chat_messages (id, chat_id, role, content, model)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING *
        """,
        str(uuid.uuid4()), chat_id, role, content, model,
    )
    return dict(row)
