# app/core/middleware.py
from typing import Iterable, List, Optional, Tuple, Set
import re

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette import status

# match security.py: decode_token / InvalidTokenError / is_access_token
try:
    from .security import decode_token, InvalidTokenError, is_access_token
except ImportError:
    from app.core.security import decode_token, InvalidTokenError, is_access_token


def _is_whitelisted(path: str, white: Iterable[re.Pattern[str]]) -> bool:
    return any(p.match(path) for p in white)


class RequireAuthMiddleware(BaseHTTPMiddleware):
    """
    Global auth gate:
      - Non-whitelisted paths must carry a Bearer access token.
      - Token is decoded via security.decode_token (HS256 + SECRET).
      - Only tokens with type == 'access' are accepted.
      - On success, attaches a small user context to request.state.user.
      - Optional coarse RBAC by path prefix (role_rules).
      - Fine-grained, object-level checks should stay in route dependencies.
    """

    def __init__(
        self,
        app,
        *,
        allow_anonymous: Optional[List[re.Pattern[str]]] = None,
        role_rules: Optional[List[Tuple[re.Pattern[str], Set[str]]]] = None,
    ):
        super().__init__(app)
        self.allow_anonymous = allow_anonymous or [
            re.compile(r"^/api/auth/.*$"),   # register/login/me
            re.compile(r"^/docs$"),
            re.compile(r"^/redoc$"),
            re.compile(r"^/openapi\.json$"),
            re.compile(r"^/healthz$"),
        ]
        self.role_rules = role_rules or [
            # (re.compile(r"^/api/admin/"), {"admin"}),
            # (re.compile(r"^/api/doctor/"), {"doctor", "admin"}),
        ]

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # 1) Whitelist pass-through
        if _is_whitelisted(path, self.allow_anonymous):
            return await call_next(request)

        # 2) Require Bearer header
        auth = request.headers.get("authorization") or request.headers.get("Authorization")
        if not auth or not auth.lower().startswith("bearer "):
            return JSONResponse(
                {"detail": "Missing or invalid Authorization header"},
                status_code=status.HTTP_401_UNAUTHORIZED,
            )
        token = auth.split(" ", 1)[1].strip()
        if not token:
            return JSONResponse({"detail": "Empty bearer token"}, status_code=status.HTTP_401_UNAUTHORIZED)

        # 3) Decode & validate
        try:
            payload = decode_token(token)  # may raise InvalidTokenError
        except InvalidTokenError:
            return JSONResponse({"detail": "Invalid or expired token"}, status_code=status.HTTP_401_UNAUTHORIZED)

        # 4) Must be an access token
        if not is_access_token(payload):
            return JSONResponse({"detail": "Wrong token type"}, status_code=status.HTTP_401_UNAUTHORIZED)

        # 5) Minimal claim checks (role is required for RBAC)
        user_id = payload.get("sub")
        role = payload.get("role")
        if not role:
            return JSONResponse({"detail": "Token missing role claim"}, status_code=status.HTTP_401_UNAUTHORIZED)

        # Attach a small, convenient user context (dict) for handlers/guards
        request.state.user = {
            "sub": user_id,                 # UUID string
            "role": role,                   # "patient" | "doctor" | "admin"
            "email": payload.get("email"),
            "scopes": payload.get("scopes") or [],
            "jti": payload.get("jti"),
        }

        # 6) Optional: prefix-based coarse RBAC
        for pattern, allowed in self.role_rules:
            if pattern.match(path) and role not in allowed:
                return JSONResponse({"detail": "Forbidden (role not allowed)"}, status_code=status.HTTP_403_FORBIDDEN)

        # 7) Continue
        return await call_next(request)
