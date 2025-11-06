
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

# LOAD ENVIRONMENT VARIABLE (.env) — OPTIONAL
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv() # automatically read .env file and add to os.environ
except Exception:
    # if dotenv is not available or error 
    # -> skip (still use existing environment variables)
    pass

# FUNCTION TO GET ENVIRONMENT VARIABLES
def env_get(key: str, default: str | None = None) -> str:
    """
        Get the value of environment variable (key).
        If none or empty -> stop the program with an error message.
    """
    val = os.getenv(key, default)
    if val is None or val == "":
        raise SystemExit(f"[restore] Missing required environment variable: {key}")
    return val

# GET THE LATEST BACKUP FILE IN THE FOLDER
def latest_backup(backup_dir: Path) -> Path | None:
    """
        Find the latest *.sql.gz file (sorted by name descending).
        Requires filenames containing lexicographically increasing timestamps (YYYYmmddHHMMSS).
    """
    cand = sorted(backup_dir.glob("*.sql.gz"), key=lambda p: p.name, reverse=True)
    return cand[0] if cand else None


# DATA RECOVERY
def main() -> int:
    # Read command line arguments
    parser = argparse.ArgumentParser(description="PostgreSQL restore tool")
    parser.add_argument("--file", type=str, help="backup file (.sql.gz) to restore from")
    parser.add_argument("--drop-schema", action="store_true", help="drop schema public CASCADE before restore")
    parser.add_argument("--yes", action="store_true", help="auto-confirm without prompt")
    args = parser.parse_args()

    # Get DB connection information from environment variable
    dbname = env_get("DB_NAME")
    dbuser = env_get("DB_USER")
    dbpass = env_get("DB_PASSWORD")
    dbhost = env_get("DB_HOST", "localhost")
    dbport = env_get("DB_PORT", "5432")
    backup_dir = Path(os.getenv("BACKUP_DIR", "./backups")).resolve()
    backup_dir.mkdir(parents=True, exist_ok=True) # make sure the directory exists

    # Specify the source file to restore
    if args.file:
        # If user specifies a specific file via --file
        src = Path(args.file).resolve()
    else:
        # Otherwise, manually select the latest version in BACKUP_DIR
        src = latest_backup(backup_dir)
        if not src:
            raise SystemExit(f"[restore] No backup files found in {backup_dir}")

    #Check existence & format *.sql.gz
    if not src.exists() or not src.suffixes[-2:] == ['.sql', '.gz']:
        raise SystemExit(f"[restore] File not found or not .sql.gz: {src}")

    print(f"[restore] Restoring from: {src}")

    # Confirm dangerous operation (if no --yes)
    if not args.yes:
        ans = input("This will modify database. Proceed? [y/N]: ").strip().lower()
        if ans != 'y':
            print("[restore] Aborted.")
            return 0

    # Check if 'psql' is in PATH
    psql = shutil.which("psql")
    if not psql:
        raise SystemExit("[restore] 'psql' not found in PATH. Install PostgreSQL client tools.")

    # Prepare ENV to pass to psql (set PGPASSWORD)
    env = os.environ.copy()
    env["PGPASSWORD"] = dbpass

    # (Optional) Clear the schema before restoring
    if args.drop_schema:
        print("[restore] Dropping schema public CASCADE...")
        # -v ON_ERROR_STOP=1: stop immediately if an error occurs
        drop_cmd = [psql, "-h", dbhost, "-p", str(dbport), "-U", dbuser, "-d", dbname, "-v", "ON_ERROR_STOP=1"]

        # Send SQL statements directly to stdin:
        # DROP SCHEMA ... CASCADE; -> delete all objects in the public schema
        # CREATE SCHEMA public; -> recreate the empty schema
        proc = subprocess.run(
            drop_cmd,
            input=b"DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public;",
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )


        if proc.returncode != 0:
            # Print stderr to show the user errors from PostgreSQL
            sys.stderr.write(proc.stderr.decode("utf-8", errors="ignore"))
            return proc.returncode

    # Unpack & load dump into DB in one transaction
    print("[restore] Loading SQL into database (single-transaction)...")

    # -1: execute in single-transaction mode (commit if successful, rollback if all errors)
    # -v ON_ERROR_STOP=1: stop any error immediately
    restore_cmd = [psql, "-h", dbhost, "-p", str(dbport), "-U", dbuser, "-d", dbname, "-v", "ON_ERROR_STOP=1", "-1"]

    # Open .sql.gz file and read SQL data (compressed) -> decompress to RAM
    with gzip.open(src, "rb") as f:
        data = f.read()

    # Run psql, pass SQL content to stdin
    proc = subprocess.run(restore_cmd, input=data, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # If there is an error during restore, print stderr and return the error code
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr.decode("utf-8", errors="ignore"))
        return proc.returncode
    

    print("[restore] Done.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
