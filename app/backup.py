# app/backup.py
import argparse
import datetime as dt
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
    # Fallback: dùng .env nếu có
    try:
        from dotenv import load_dotenv  # type: ignore
        load_dotenv()
    except Exception:
        pass


def env_get(key: str, default: str | None = None) -> str:
    """
    Get old-style environment variables (DB_NAME, DB_USER, ...).
    Only use if there is no SQL_DSN in settings / env. 
    """
    val = os.getenv(key, default)
    if val is None or val == "":
        raise SystemExit(f"[backup] Missing required environment variable: {key}")
    return val


def get_db_conn_params() -> tuple[str, str, str, str, str]:
    """
    Get DB connection information for pg_dump.

    Priority:
      1) settings.SQL_DSN (config mới)
      2) env SQL_DSN
      3) bộ biến cũ: DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT
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
            raise SystemExit(
                "[backup] SQL_DSN must contain username, password and database name"
            )
        return dbname, user, password, host, port

    # Fallback: use old style envs
    dbname = env_get("DB_NAME")
    user = env_get("DB_USER")
    password = env_get("DB_PASSWORD")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    return dbname, user, password, host, str(port)


def ensure_tool(name: str) -> str:
    """
    Check if command like pg_dump is in PATH.
    If not, stop the program.
    """
    path = shutil.which(name)
    if not path:
        raise SystemExit(f"[backup] Tool '{name}' not found in PATH. Install PostgreSQL client tools.")
    return path


def rotate_backups(backup_dir: Path, keep_days: int) -> list[Path]:
    """
    Delete *.sql.gz backup files older than keep_days days.
    """
    cutoff = dt.datetime.now() - dt.timedelta(days=keep_days)
    removed: list[Path] = []

    for f in sorted(backup_dir.glob("*.sql.gz")):
        try:
            # file name format: <dbname>-YYYYmmddHHMMSS.sql.gz
            ts_str = f.stem.split("-")[-1]
            ts = dt.datetime.strptime(ts_str, "%Y%m%d%H%M%S")
        except Exception:
            # If the name is not in the correct format, ignore it.
            continue

        if ts < cutoff:
            f.unlink(missing_ok=True)
            removed.append(f)

    return removed


def main() -> int:
    parser = argparse.ArgumentParser(description="PostgreSQL backup creator")
    parser.add_argument(
        "--keep", type=int, default=None,
        help="days to keep backups (override KEEP_DAYS)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="show what would happen without executing",
    )
    args = parser.parse_args()

    # Get DB info from SQL_DSN (or old env)
    dbname, dbuser, dbpass, dbhost, dbport = get_db_conn_params()

    # Backup directory (can set BACKUP_DIR in .env, otherwise default ./backups)
    backup_dir = Path(os.getenv("BACKUP_DIR", "./backups")).resolve()
    keep_days = int(args.keep if args.keep is not None else os.getenv("KEEP_DAYS", 14))

    backup_dir.mkdir(parents=True, exist_ok=True)

    # File name by timestamp
    ts = dt.datetime.now().strftime("%Y%m%d%H%M%S")
    sql_path = backup_dir / f"{dbname}-{ts}.sql"
    gz_path = Path(str(sql_path) + ".gz")

    pg_dump = ensure_tool("pg_dump")

    cmd = [
        pg_dump,
        "-h", dbhost,
        "-p", str(dbport),
        "-U", dbuser,
        "-d", dbname,
        "--no-owner",
        "--no-privileges",
        "-F", "p",  # plain SQL
    ]

    print(f"[backup] Output: {gz_path}")
    print(f"[backup] Using: {pg_dump}")
    print(f"[backup] Keep days: {keep_days} (rotation before backup)")

    # Delete old files
    removed = rotate_backups(backup_dir, keep_days)
    if removed:
        print("[backup] Rotated (deleted old):")
        for p in removed:
            print("  -", p.name)

    if args.dry_run:
        print("[backup] DRY RUN — not executing pg_dump")
        return 0

    env = os.environ.copy()
    env["PGPASSWORD"] = dbpass  # avoid leaving passwords in the command line

    # run pg_dump → write to .sql file
    with sql_path.open("wb") as f:
        proc = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, env=env)

    if proc.returncode != 0:
        err = proc.stderr.decode("utf-8", errors="ignore")
        sql_path.unlink(missing_ok=True)
        print(err, file=sys.stderr)
        return proc.returncode

    # gzip
    with sql_path.open("rb") as src, gzip.open(gz_path, "wb") as dst:
        shutil.copyfileobj(src, dst)
    sql_path.unlink(missing_ok=True)

    print(f"[backup] Done. Size: {gz_path.stat().st_size} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())