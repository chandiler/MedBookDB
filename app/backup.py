# app/backup.py (modificado)
import argparse
import datetime as dt
import gzip
import os
import shutil
import subprocess
import sys
from pathlib import Path

# CAMBIO: Importar la configuración centralizada
try:
    from app.core.config import settings
    HAS_APP_CONFIG = True
except ImportError:
    HAS_APP_CONFIG = False
    # Fallback a variables de entorno
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except Exception:
        pass

def env_get(key: str, default: str | None = None) -> str:
    # Si tenemos configuración de la app, úsala primero
    if HAS_APP_CONFIG:
        if hasattr(settings, key):
            return getattr(settings, key)
        # Mapeo de nombres alternativos
        mapping = {
            'DB_NAME': 'DATABASE_NAME',
            'DB_USER': 'DATABASE_USER', 
            'DB_PASSWORD': 'DATABASE_PASSWORD',
            'DB_HOST': 'DATABASE_HOST',
            'DB_PORT': 'DATABASE_PORT'
        }
        if key in mapping and hasattr(settings, mapping[key]):
            return getattr(settings, mapping[key])
    
    # Fallback a variables de entorno
    val = os.getenv(key, default)
    if val is None or val == "":
        raise SystemExit(f"[backup] Missing required environment variable: {key}")
    return val

# ... resto del código igual