
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

# app/restore.py
import argparse
import gzip
import os
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

try:
    from app.core.config import settings
    HAS_APP_CONFIG = True
except ImportError:
    HAS_APP_CONFIG = False
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except Exception:
        pass


def get_db_conn_params() -> tuple[str, str, str, str, str]:
    """
    Extract DB name, user, password, host, port
    — SQL_DSN priority of Settings
    — if not present then fallback to env DB_NAME / DB_USER / ... 
    """
    dsn = ""
    if HAS_APP_CONFIG:
        dsn = getattr(settings, "SQL_DSN", "") or ""
    if not dsn:
        dsn = os.getenv("SQL_DSN", "")

    if dsn:
        parsed = urlparse(dsn)
        dbname = (parsed.path or "").lstrip("/")
        user = parsed.username
        password = parsed.password
        host = parsed.hostname or "localhost"
        port = str(parsed.port or 5432)

        if not (user and password and dbname):
            raise SystemExit("[restore] SQL_DSN must include user, password and db name")
        return dbname, user, password, host, port

    dbname = os.getenv("DB_NAME")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")

    if not (dbname and user and password):
        raise SystemExit("[restore] Missing DB env variables")

    return dbname, user, password, host, port


def latest_backup(dir: Path) -> Path | None:
    cand = sorted(dir.glob("*.sql.gz"), key=lambda p: p.name, reverse=True)
    return cand[0] if cand else None


def main() -> int:
    parser = argparse.ArgumentParser(description="PostgreSQL restore tool")
    parser.add_argument("--file", type=str, help="backup file (.sql.gz) to restore from")
    parser.add_argument("--drop-schema", action="store_true", help="DROP SCHEMA public CASCADE before restore")
    parser.add_argument("--yes", action="store_true", help="Automatically confirm without prompt")
    args = parser.parse_args()

    dbname, dbuser, dbpass, dbhost, dbport = get_db_conn_params()

    backup_dir = Path(os.getenv("BACKUP_DIR", "./backups")).resolve()
    backup_dir.mkdir(parents=True, exist_ok=True)

    # Determine backup file
    if args.file:
        src = Path(args.file).resolve()
    else:
        src = latest_backup(backup_dir)
        if not src:
            raise SystemExit(f"[restore] No backups found in: {backup_dir}")

    if not src.exists() or not src.suffixes[-2:] == [".sql", ".gz"]:
        raise SystemExit(f"[restore] File invalid or not .sql.gz: {src}")

    print(f"[restore] Restoring from: {src}")

    if not args.yes:
        ans = input("WARNING: This will alter database. Continue? [y/N]: ").strip().lower()
        if ans != "y":
            print("[restore] Aborted.")
            return 0

    psql = shutil.which("psql")
    if not psql:
        raise SystemExit("[restore] 'psql' not found in PATH.")

    env = os.environ.copy()
    env["PGPASSWORD"] = dbpass

    if args.drop_schema:
        print("[restore] Dropping schema public...")
        drop_cmd = [
            psql,
            "-h", dbhost,
            "-p", str(dbport),
            "-U", dbuser,
            "-d", dbname,
            "-v", "ON_ERROR_STOP=1"
        ]
        proc = subprocess.run(
            drop_cmd,
            input=b"DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public;",
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if proc.returncode != 0:
            sys.stderr.write(proc.stderr.decode())
            return proc.returncode

    # RESTORE SQL DUMP
    restore_cmd = [
        psql,
        "-h", dbhost,
        "-p", str(dbport),
        "-U", dbuser,
        "-d", dbname,
        "-v", "ON_ERROR_STOP=1",
        "-1",  # single-transaction
    ]

    print("[restore] Loading SQL into DB...")

    with gzip.open(src, "rb") as f:
        data = f.read()

    proc = subprocess.run(restore_cmd, input=data, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if proc.returncode != 0:
        sys.stderr.write(proc.stderr.decode())
        return proc.returncode

    print("[restore] SUCCESS.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
