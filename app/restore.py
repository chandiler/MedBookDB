#!/usr/bin/env python3
"""restore.py — restore latest PostgreSQL SQL dump (.sql.gz) safely.

Usage:
  python restore.py                    # restore from latest backup file
  python restore.py --file path.sql.gz # restore from specific file
  python restore.py --drop-schema      # drop schema public CASCADE before restore
  python restore.py --yes              # non-interactive (auto-confirm)

Env / .env variables:
  DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT
  BACKUP_DIR (default: ./backups)
"""
import argparse
import gzip
import os
import shutil
import subprocess
import sys
from pathlib import Path
from datetime import datetime

try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass

def env_get(key: str, default: str | None = None) -> str:
    val = os.getenv(key, default)
    if val is None or val == "":
        raise SystemExit(f"[restore] Missing required environment variable: {key}")
    return val

def latest_backup(backup_dir: Path) -> Path | None:
    cand = sorted(backup_dir.glob("*.sql.gz"), key=lambda p: p.name, reverse=True)
    return cand[0] if cand else None

def main() -> int:
    parser = argparse.ArgumentParser(description="PostgreSQL restore tool")
    parser.add_argument("--file", type=str, help="backup file (.sql.gz) to restore from")
    parser.add_argument("--drop-schema", action="store_true", help="drop schema public CASCADE before restore")
    parser.add_argument("--yes", action="store_true", help="auto-confirm without prompt")
    args = parser.parse_args()

    dbname = env_get("DB_NAME")
    dbuser = env_get("DB_USER")
    dbpass = env_get("DB_PASSWORD")
    dbhost = env_get("DB_HOST", "localhost")
    dbport = env_get("DB_PORT", "5432")
    backup_dir = Path(os.getenv("BACKUP_DIR", "./backups")).resolve()
    backup_dir.mkdir(parents=True, exist_ok=True)

    if args.file:
        src = Path(args.file).resolve()
    else:
        src = latest_backup(backup_dir)
        if not src:
            raise SystemExit(f"[restore] No backup files found in {backup_dir}")

    if not src.exists() or not src.suffixes[-2:] == ['.sql', '.gz']:
        raise SystemExit(f"[restore] File not found or not .sql.gz: {src}")

    print(f"[restore] Restoring from: {src}")
    if not args.yes:
        ans = input("This will modify database. Proceed? [y/N]: ").strip().lower()
        if ans != 'y':
            print("[restore] Aborted.")
            return 0

    psql = shutil.which("psql")
    if not psql:
        raise SystemExit("[restore] 'psql' not found in PATH. Install PostgreSQL client tools.")

    env = os.environ.copy()
    env["PGPASSWORD"] = dbpass

    if args.drop_schema:
        print("[restore] Dropping schema public CASCADE...")
        drop_cmd = [psql, "-h", dbhost, "-p", str(dbport), "-U", dbuser, "-d", dbname, "-v", "ON_ERROR_STOP=1"]
        proc = subprocess.run(drop_cmd, input=b"DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public;", env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            sys.stderr.write(proc.stderr.decode("utf-8", errors="ignore"))
            return proc.returncode

    print("[restore] Loading SQL into database (single-transaction)...")
    restore_cmd = [psql, "-h", dbhost, "-p", str(dbport), "-U", dbuser, "-d", dbname, "-v", "ON_ERROR_STOP=1", "-1"]
    with gzip.open(src, "rb") as f:
        data = f.read()
    proc = subprocess.run(restore_cmd, input=data, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr.decode("utf-8", errors="ignore"))
        return proc.returncode
    print("[restore] Done.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
