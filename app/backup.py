
#!/usr/bin/env python3
"""backup.py — PostgreSQL logical backup (plain SQL + gzip) with rotation.

Usage:
  python backup.py            # creates timestamped .sql.gz in BACKUP_DIR
  python backup.py --keep 14  # override KEEP_DAYS for this run
  python backup.py --dry-run  # show actions without running pg_dump

Env / .env variables (loaded via python-dotenv if present):
  DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT
  BACKUP_DIR (default: ./backups)
  KEEP_DAYS  (default: 14)

Requirements:
  - PostgreSQL client tools in PATH (pg_dump)
"""
import argparse
import datetime as dt
import gzip
import os
import shutil
import subprocess
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass  # optional

def env_get(key: str, default: str | None = None) -> str:
    val = os.getenv(key, default)
    if val is None or val == "":
        raise SystemExit(f"[backup] Missing required environment variable: {key}")
    return val

def ensure_tool(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise SystemExit(f"[backup] Tool '{name}' not found in PATH. Install PostgreSQL client tools.")
    return path

def rotate_backups(backup_dir: Path, keep_days: int) -> list[Path]:
    cutoff = dt.datetime.now() - dt.timedelta(days=keep_days)
    removed: list[Path] = []
    for f in sorted(backup_dir.glob("*.sql.gz")):
        try:
            ts_str = f.stem.split("-")[-1]  # expecting name-YYYYmmddHHMMSS.sql.gz
            ts = dt.datetime.strptime(ts_str, "%Y%m%d%H%M%S")
        except Exception:
            # Skip files that don't match pattern
            continue
        if ts < cutoff:
            f.unlink(missing_ok=True)
            removed.append(f)
    return removed

def main() -> int:
    parser = argparse.ArgumentParser(description="PostgreSQL backup creator")
    parser.add_argument("--keep", type=int, default=None, help="days to keep backups (override KEEP_DAYS)")
    parser.add_argument("--dry-run", action="store_true", help="show what would happen without executing")
    args = parser.parse_args()

    dbname = env_get("DB_NAME")
    dbuser = env_get("DB_USER")
    dbpass = env_get("DB_PASSWORD")
    dbhost = env_get("DB_HOST", "localhost")
    dbport = env_get("DB_PORT", "5432")
    backup_dir = Path(os.getenv("BACKUP_DIR", "./backups")).resolve()
    keep_days = int(args.keep if args.keep is not None else os.getenv("KEEP_DAYS", 14))

    backup_dir.mkdir(parents=True, exist_ok=True)
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
        "--no-owner", "--no-privileges",
        "-F", "p",  # plain SQL
    ]

    print(f"[backup] Output: {gz_path}")
    print(f"[backup] Using: {pg_dump}")
    print(f"[backup] Keep days: {keep_days} (rotation before backup)")

    removed = rotate_backups(backup_dir, keep_days)
    if removed:
        print("[backup] Rotated (deleted old):\n  - " + "\n  - ".join(str(p.name) for p in removed))

    if args.dry_run:
        print("[backup] DRY RUN — not executing pg_dump")
        return 0

    # Run pg_dump and capture stdout, then gzip
    env = os.environ.copy()
    env["PGPASSWORD"] = dbpass  # safer than putting in cmd
    with sql_path.open("wb") as f:
        proc = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, env=env)
    if proc.returncode != 0:
        err = proc.stderr.decode("utf-8", errors="ignore")
        sql_path.unlink(missing_ok=True)
        print(err, file=sys.stderr)
        return proc.returncode

    # gzip the file
    with sql_path.open("rb") as src, gzip.open(gz_path, "wb") as dst:
        shutil.copyfileobj(src, dst)
    sql_path.unlink(missing_ok=True)  # remove uncompressed
    print(f"[backup] Done. Size: {gz_path.stat().st_size} bytes")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
