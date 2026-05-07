"""
Tabular review — Foundry Invocations protocol (batch JSON in/out).
Replaces backend/src/routes/tabular.ts.
"""

from fastapi import APIRouter, Depends, Request
from app.auth.middleware import require_auth

router = APIRouter()


@router.post("/invocations")
async def tabular_invocations(request: Request, _=Depends(require_auth)):
    """
    Foundry Invocations protocol endpoint for batch tabular extraction.
    Input: { document_ids: string[], columns: string[] }
    Output: { results: { doc_id, column, value }[] }
    Placeholder — full implementation in python-tools todo.
    """
    body = await request.json()
    return {"status": "accepted", "input": body}
