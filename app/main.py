# app/main.py
from fastapi import FastAPI
from app.core.config import settings
from app.routers import health, auth
from app.api.routes import admin,doctor
from app.api.routes import dev
from app.api.routes import users

# import middleware and regex
import re
from app.core.middleware import RequireAuthMiddleware

app = FastAPI(title="Secure Healthcare Appointment System")

# ===== Middleware (global auth gate) =====
# Construct whitelist and role rules based on /api prefix
API = re.escape(settings.API_PREFIX.rstrip("/"))  # e.g. "/api"

ALLOW_ANONYMOUS = [
    re.compile(rf"^{API}/auth/.*$"),     # register/login/me
    re.compile(rf"^{API}/health/.*$"),   # health endpoints
    re.compile(rf"^{API}/health/?$"),    # match /api/health & /api/health/
    re.compile(r"^/docs$"),
    re.compile(r"^/redoc$"),
    re.compile(r"^/openapi\.json$"),
    re.compile(r"^/healthz$"),
]

ROLE_RULES = [
    # These prefix routes require corresponding roles (adjust according to your actual route naming)
    re.compile(rf"^{API}/admin/"),  {"admin"},
    re.compile(rf"^{API}/doctor/"), {"doctor", "admin"},
]
# Passed in as List[Tuple[Pattern, Set[str]]]
ROLE_RULES = [(ROLE_RULES[i], ROLE_RULES[i+1]) for i in range(0, len(ROLE_RULES), 2)]

app.add_middleware(
    RequireAuthMiddleware,
    allow_anonymous=ALLOW_ANONYMOUS,
    role_rules=ROLE_RULES
)
# ===== /Middleware =====

# Routing
app.include_router(health.router, prefix=settings.API_PREFIX, tags=["health"])
app.include_router(auth.router,   prefix=settings.API_PREFIX, tags=["auth"])
app.include_router(admin.router, prefix=settings.API_PREFIX, tags=["admin"])
app.include_router(doctor.router, prefix=settings.API_PREFIX, tags=["doctor"])
app.include_router(dev.router, prefix=settings.API_PREFIX, tags=["dev"])
app.include_router(users.router, prefix=settings.API_PREFIX, tags=["users"])

@app.get("/")
def root():
    return {"message": "Healthcare System API running successfully"}


from fastapi.routing import APIRoute
for r in app.routes:
    if isinstance(r, APIRoute):
        print("ROUTE:", r.path, r.methods)




