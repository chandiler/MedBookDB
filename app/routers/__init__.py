# app/routers/__init__.py
from . import health
from . import auth
from . import patients
from . import admin

__all__ = ["health", "auth", "patients", "admin"]