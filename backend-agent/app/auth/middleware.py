"""
Entra External ID JWT validation middleware.
Replaces backend/src/middleware/auth.ts (Supabase JWT validation).

Validates Bearer tokens issued by Entra External ID and extracts
user_id + email into request.state for downstream route handlers.
"""

import jwt
from jwt import PyJWKClient
from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import settings

_bearer = HTTPBearer()

# JWKS endpoint for Entra External ID (CIAM)
_JWKS_URL = (
    f"https://{settings.entra_tenant_id}.ciamlogin.com"
    f"/{settings.entra_tenant_id}.onmicrosoft.com/discovery/v2.0/keys"
)
_jwks_client = PyJWKClient(_JWKS_URL) if settings.entra_tenant_id else None


async def require_auth(request: Request) -> dict:
    """
    FastAPI dependency. Validates the Entra JWT and returns the claims dict.
    Sets request.state.user_id and request.state.user_email.
    """
    auth: HTTPAuthorizationCredentials = await _bearer(request)
    token = auth.credentials

    if not _jwks_client:
        raise HTTPException(status_code=500, detail="Auth not configured")

    try:
        signing_key = _jwks_client.get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.entra_client_id,
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

    user_id: str = claims.get("sub") or claims.get("oid", "")
    user_email: str = (claims.get("email") or claims.get("preferred_username", "")).lower()

    if not user_id:
        raise HTTPException(status_code=401, detail="Token missing subject claim")

    request.state.user_id = user_id
    request.state.user_email = user_email
    return claims
