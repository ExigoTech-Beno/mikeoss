"""Workflows routes. Replaces backend/src/routes/workflows.ts."""

from fastapi import APIRouter, Depends, Request
from app.auth.middleware import require_auth
from app.plugins.workflows import BUILTIN_WORKFLOWS

router = APIRouter()


@router.get("/builtin")
async def list_builtin_workflows(_=Depends(require_auth)):
    return [{"id": w["id"], "title": w["title"]} for w in BUILTIN_WORKFLOWS]
