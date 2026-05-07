"""User profile routes. Replaces backend/src/routes/user.ts."""

from fastapi import APIRouter, Depends, Request
from app.auth.middleware import require_auth
from app.db.connection import get_pool
from app.db.models import get_user_profile, upsert_user_profile

router = APIRouter()


@router.get("/me")
async def get_me(request: Request, _=Depends(require_auth)):
    db = await get_pool()
    profile = await get_user_profile(db, request.state.user_id)
    if not profile:
        profile = await upsert_user_profile(db, request.state.user_id, request.state.user_email)
    return profile
