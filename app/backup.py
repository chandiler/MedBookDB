# app/backup.py (modified)
import argparse
import datetime as dt
import gzip
import os
import shutil
import subprocess
import sys
from pathlib import Path

# CHANGE: Import centralized configuration
try:
    from app.core.config import settings
    HAS_APP_CONFIG = True
except ImportError:
    HAS_APP_CONFIG = False
    # Fallback to environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except Exception:
        pass

def env_get(key: str, default: str | None = None) -> str:
    # If we have app configuration, use it first
    if HAS_APP_CONFIG:
        if hasattr(settings, key):
            return getattr(settings, key)
        # Alternative name mapping
        mapping = {
            'DB_NAME': 'DATABASE_NAME',
            'DB_USER': 'DATABASE_USER', 
            'DB_PASSWORD': 'DATABASE_PASSWORD',
            'DB_HOST': 'DATABASE_HOST',
            'DB_PORT': 'DATABASE_PORT'
        }
        if key in mapping and hasattr(settings, mapping[key]):
            return getattr(settings, mapping[key])
    
    # Fallback to environment variables
    val = os.getenv(key, default)
    if val is None or val == "":
        raise SystemExit(f"[backup] Missing required environment variable: {key}")
    return val

# ... rest of the code unchanged