# routes/admin_api.py
import os
import sys
import subprocess
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel

router = APIRouter(prefix="/admin", tags=["admin"])


# ========== Simple token check ==========
def verify_admin(x_admin_token: str = Header(None)):
    """Very simple header token guard for dangerous operations."""
    expected = os.getenv("ADMIN_TOKEN")
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ADMIN_TOKEN is not set on server",
        )
    if x_admin_token != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin token")
    return True


# ========== Helper to run backup/restore scripts ==========
def run_py_module(mod: str, args: list[str]) -> tuple[int, str, str]:
    """Run 'python -m <mod> <args...>' and capture stdout/stderr."""
    cmd = [sys.executable, "-m", mod, *args]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return proc.returncode, proc.stdout.decode("utf-8", "ignore"), proc.stderr.decode("utf-8", "ignore")


# ========== Models ==========
class RestoreReq(BaseModel):
    file: Optional[str] = None        # path to .sql.gz; if None → latest
    drop_schema: bool = False         # dangerous; wipes public schema before restore


# ========== API endpoints ==========
@router.post("/backup-now")
def backup_now(_: bool = Depends(verify_admin)):
    """Trigger an immediate database backup."""
    code, out, err = run_py_module("app.backup", [])

    backup_dir = Path(os.getenv("BACKUP_DIR", "./backups")).resolve()
    latest = None
    if backup_dir.exists():
        files = sorted(backup_dir.glob("*.sql.gz"), key=lambda p: p.name, reverse=True)
        latest = str(files[0]) if files else None

    return {
        "ok": code == 0,
        "exit_code": code,
        "latest_file": latest,
        "stdout": out.strip(),
        "stderr": err.strip(),
    }


@router.post("/restore-latest")
def restore_latest(req: RestoreReq, _: bool = Depends(verify_admin)):
    """Restore from latest (or specified) backup file."""
    args: list[str] = ["--yes"]
    if req.drop_schema:
        args.append("--drop-schema")
    if req.file:
        args += ["--file", req.file]

    code, out, err = run_py_module("app.restore", args)
    return {
        "ok": code == 0,
        "exit_code": code,
        "stdout": out.strip(),
        "stderr": err.strip(),
    }