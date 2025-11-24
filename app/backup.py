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

# CHECK FOR TOOL EXISTENCE (pg_dump)
def ensure_tool(name: str) -> str:
    """
        Find the execution location (path) of a command like pg_dump in the system.
        If not found -> stop the program.
    """
    path = shutil.which(name)
    if not path:
        raise SystemExit(f"[backup] Tool '{name}' not found in PATH. Install PostgreSQL client tools.")
    return path


# DELETE OLD EXPIRED BACKUP FILES
def rotate_backups(backup_dir: Path, keep_days: int) -> list[Path]:
    """
        Delete backup files (*.sql.gz) older than the number of days to keep (keep_days).
    """
    # calculate expiration time
    cutoff = dt.datetime.now() - dt.timedelta(days=keep_days)

    removed: list[Path] = []

    # browse all .sql.gz files in the directory
    for f in sorted(backup_dir.glob("*.sql.gz")):
        try:
            # Expected file name: name-YYYYmmddHHMMSS.sql.gz -> get the timestamp part
            ts_str = f.stem.split("-")[-1]
            ts = dt.datetime.strptime(ts_str, "%Y%m%d%H%M%S")
        except Exception:
            # If the file name is not in the correct format -> ignore
            continue
        # If the file is older than cutoff -> delete
        if ts < cutoff:
            f.unlink(missing_ok=True)
            removed.append(f)
    return removed

# CREATE BACKUP
def main() -> int:
    # Read command line arguments
    parser = argparse.ArgumentParser(description="PostgreSQL backup creator")
    parser.add_argument("--keep", type=int, default=None, help="days to keep backups (override KEEP_DAYS)")
    parser.add_argument("--dry-run", action="store_true", help="show what would happen without executing")
    args = parser.parse_args()

    # Get DB connection information from environment variable
    dbname = env_get("DB_NAME")
    dbuser = env_get("DB_USER")
    dbpass = env_get("DB_PASSWORD")
    dbhost = env_get("DB_HOST", "localhost")
    dbport = env_get("DB_PORT", "5432")
    backup_dir = Path(os.getenv("BACKUP_DIR", "./backups")).resolve()
    keep_days = int(args.keep if args.keep is not None else os.getenv("KEEP_DAYS", 14))

    # Create a backup folder if it doesn't exist yet
    backup_dir.mkdir(parents=True, exist_ok=True)

    # Create file name according to timestamp
    ts = dt.datetime.now().strftime("%Y%m%d%H%M%S")
    sql_path = backup_dir / f"{dbname}-{ts}.sql"
    gz_path = Path(str(sql_path) + ".gz")

    # Check if there is pg_dump tool
    pg_dump = ensure_tool("pg_dump")

    # Create pg_dump command
    cmd = [
        pg_dump,
        "-h", dbhost,
        "-p", str(dbport),
        "-U", dbuser,
        "-d", dbname,
        # remove ownership information for easy restore
        "--no-owner", "--no-privileges",
        # plain SQL format (text file)
        "-F", "p",
    ]

    # Print information to console
    print(f"[backup] Output: {gz_path}")
    print(f"[backup] Using: {pg_dump}")
    print(f"[backup] Keep days: {keep_days} (rotation before backup)")

    # Rotate old backup files
    removed = rotate_backups(backup_dir, keep_days)
    if removed:
        print("[backup] Rotated (deleted old):\n  - " + "\n  - ".join(str(p.name) for p in removed))

    # Simulation mode (dry-run)
    if args.dry_run:
        print("[backup] DRY RUN — not executing pg_dump")
        return 0

    # Run pg_dump to export DB to .sql file
    env = os.environ.copy()
    # set password via environment variable
    env["PGPASSWORD"] = dbpass

    # Open .sql file for writing
    with sql_path.open("wb") as f:
        # subprocess.run runs the pg_dump command, writes stdout to a file, stderr catches errors
        proc = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, env=env)

    # If pg_dump returns an error (returncode != 0)
    if proc.returncode != 0:
        err = proc.stderr.decode("utf-8", errors="ignore")
        # delete incomplete .sql file
        sql_path.unlink(missing_ok=True)
        print(err, file=sys.stderr)
        return proc.returncode

    # Compress .sql file to .sql.gz
    with sql_path.open("rb") as src, gzip.open(gz_path, "wb") as dst:
        # copy all content from src to dst (gzip compression)
        shutil.copyfileobj(src, dst)
    # delete original .sql file after compression
    sql_path.unlink(missing_ok=True)

    # Print result
    print(f"[backup] Done. Size: {gz_path.stat().st_size} bytes")

    # exit code 0 = success
    return 0

if __name__ == "__main__":
    # Call main() and exit with the corresponding exit code
    raise SystemExit(main())
