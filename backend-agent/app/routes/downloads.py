"""Secure download token routes. Replaces backend/src/routes/downloads.ts."""

from fastapi import APIRouter, Depends, Request, HTTPException
from app.auth.middleware import require_auth
from app.storage.blob import get_signed_url

router = APIRouter()


@router.get("/{key:path}")
async def download_redirect(key: str, request: Request, _=Depends(require_auth)):
    url = await get_signed_url(key, expires_in=300)
    if not url:
        raise HTTPException(status_code=404, detail="File not found")
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=url)
