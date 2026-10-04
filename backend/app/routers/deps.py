"""Authentication dependencies. The actor for chain of custody ALWAYS comes from the verified JWT."""
from typing import Optional

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.database import get_db
from app.services import auth_service
from app.utils.actor import Actor
from app.utils.errors import AppError

_bearer = HTTPBearer(auto_error=False, description="JWT from POST /api/auth/login")


def _token_from_request(request: Request, creds: Optional[HTTPAuthorizationCredentials]) -> Optional[str]:
    if creds and creds.credentials:
        return creds.credentials
    # <video src> and <img src> cannot send headers, so ONLY media endpoints accept ?token=
    path = request.url.path
    if request.method == "GET" and (path.endswith("/stream") or "/snapshots/" in path):
        return request.query_params.get("token")
    return None


def get_current_user(request: Request, creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
                     db=Depends(get_db)) -> dict:
    token = _token_from_request(request, creds)
    if not token:
        raise AppError(401, "NOT_AUTHENTICATED", "Authentication required.")
    payload = auth_service.decode_access_token(token)
    user = auth_service.get_user(db, payload["sub"])
    if not user:
        raise AppError(401, "INVALID_TOKEN", "Account no longer exists.")
    return user


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") != "admin":
        raise AppError(403, "FORBIDDEN", "Administrator role required.")
    return user


def get_actor(user: dict = Depends(get_current_user)) -> Actor:
    return Actor(user["full_name"], user["user_id"])
