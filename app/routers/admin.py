# # app/routers/admin.py
# import os
# import sys
# import subprocess
# from pathlib import Path
# from typing import Optional

# from fastapi import APIRouter, Depends, Header, HTTPException, status
# from pydantic import BaseModel

# from datetime import datetime
# from fastapi import Query

# # Create an admin router to collect administrative APIs
# router = APIRouter(prefix="/admin", tags=["admin"])


# # Simple token check
# def verify_admin(x_admin_token: str = Header(None)):
#     """
#         Authentication filter (dependency) is very simple based on headers:
#         - Client must send 'X-Admin-Token' header
#         - Compare with ADMIN_TOKEN environment variable on server
#         Used for sensitive APIs (backup/restore).
#     """
#     expected = os.getenv("ADMIN_TOKEN")
#     if not expected:
#         # Server has not configured token -> internal error
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="ADMIN_TOKEN is not set on server",
#         )
#     if x_admin_token != expected:
#         # Client sent token does not match
#         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin token")
#     return True


# # Helper to run backup/restore scripts
# def run_py_module(mod: str, args: list[str]) -> tuple[int, str, str]:
#     """
#         Runs Python module 'python -m <mod> <args...>' and collects stdout/stderr.
#         Returns tuple (exit_code, stdout, stderr).
#         Used to call app.backup / app.restore as separate subroutines.
#     """
#     # sys.executable ensures the correct current interpreter is used
#     cmd = [sys.executable, "-m", mod, *args]
#     proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
#     return proc.returncode, proc.stdout.decode("utf-8", "ignore"), proc.stderr.decode("utf-8", "ignore")


# # Models
# class RestoreReq(BaseModel):
#     """
#         Payload for API restore:
#         - file: specific path to .sql.gz file (if empty -> get latest version)
#         - drop_schema: if True, wipe public schema before restore (dangerous)
#     """
#     # path to .sql.gz; if None -> latest
#     file: Optional[str] = None
#     # dangerous; wipes public schema before restore
#     drop_schema: bool = False


# # API endpoints
# @router.post("/backup-now")
# def backup_now(_: bool = Depends(verify_admin)):
#     """
#         Trigger the backup immediately.
#         - Call the 'app.backup' module using a subprocess
#         - After running, try to find the latest .sql.gz file in BACKUP_DIR to return
#     """
#     code, out, err = run_py_module("app.backup", [])

#     backup_dir = Path(os.getenv("BACKUP_DIR", "./backups")).resolve()
#     latest = None
#     if backup_dir.exists():
#         # Sort file names in descending order (names with timestamps) to get the latest version
#         files = sorted(backup_dir.glob("*.sql.gz"), key=lambda p: p.name, reverse=True)
#         latest = str(files[0]) if files else None

#     return {
#         "ok": code == 0, # true if exit_code == 0
#         "exit_code": code, # exit code of backup process
#         "latest_file": latest, # latest backup file path (if found)
#         "stdout": out.strip(), # stdout of backup process
#         "stderr": err.strip(), # stderr of backup process (if any)
#     }


# @router.post("/restore-latest")
# def restore_latest(req: RestoreReq, _: bool = Depends(verify_admin)):
#     """
#         Restore data from backup:
#         - If req.file does not exist -> automatically select the latest file in BACKUP_DIR
#         - Allow to delete schema before restore if drop_schema=True
#         - Add '--yes' to skip confirmation prompt in restore script
#     """
#     # auto-confirm to run non-interactive
#     args: list[str] = ["--yes"]
#     if req.drop_schema:
#         args.append("--drop-schema")
#     if req.file:
#         args += ["--file", req.file]

#     code, out, err = run_py_module("app.restore", args)
#     return {
#         "ok": code == 0,
#         "exit_code": code,
#         "stdout": out.strip(),
#         "stderr": err.strip(),
#     }


# # Schemas & API: list existing backup files
# class BackupFile(BaseModel):
#     """
#         Meta information about a backup file:
#         - name: file name (e.g. healthcare_system-20251105xxxx.sql.gz)
#         - path: absolute path
#         - size_bytes: file size
#         - modified_at / created_at: time of modification/creation (ISO)
#     """
#     name: str
#     path: str
#     size_bytes: int
#     modified_at: datetime
#     created_at: datetime | None = None

# class BackupListResp(BaseModel):
#     """
#         Returned results when listing backups:
#         - backup_dir: directory containing backups (absolutely resolved)
#         - count: total number of *.sql.gz files
#         - items: list of files (by sort and limit)
#     """
#     backup_dir: str
#     count: int
#     items: list[BackupFile]


# @router.get("/backups", response_model=BackupListResp)
# def list_backups(
#     _: bool = Depends(verify_admin),
#     sort: str = Query("name", regex="^(name|mtime)$", description="Sort by 'name' or 'mtime'"),
#     order: str = Query("desc", regex="^(asc|desc)$"),
#     limit: int = Query(100, ge=1, le=1000),
# ):
#     """
#         List existing backup files in BACKUP_DIR (default ./backups):
#         - Support sort by 'name' (file name) or 'mtime' (modified time)
#         - 'order' ascending/descending
#         - 'limit' number of elements returned
#     """
#     backup_dir = Path(os.getenv("BACKUP_DIR", "./backups")).resolve()
#     backup_dir.mkdir(parents=True, exist_ok=True)

#     files = list(backup_dir.glob("*.sql.gz"))

#     # Choose sort key: by modification time (mtime) or by name
#     if sort == "mtime":
#         keyfunc = lambda p: p.stat().st_mtime
#     else:
#         keyfunc = lambda p: p.name

#     reverse = (order.lower() == "desc")
#     files_sorted = sorted(files, key=keyfunc, reverse=reverse)

#     # Convert Paths to BackupFile objects
#     items: list[BackupFile] = []
#     for p in files_sorted[:limit]:
#         st = p.stat()
#         items.append(
#             BackupFile(
#                 name=p.name,
#                 path=str(p),
#                 size_bytes=st.st_size,
#                 modified_at=datetime.fromtimestamp(st.st_mtime),
#                 created_at=datetime.fromtimestamp(st.st_ctime) if st.st_ctime else None,
#             )
#         )

#     # Returns a structure with a clear schema
#     return BackupListResp(
#         backup_dir=str(backup_dir),
#         count=len(files),
#         items=items,
#     )



# app/routers/admin.py
import os
import sys
import subprocess
from pathlib import Path
from typing import Optional

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel

from app.dependencies import require_roles
from app.modules.users.models import User  # type-hint current admin

# Router for administrative APIs
router = APIRouter(prefix="/admin", tags=["admin"])

# Allow admin only (JWT)

# Create dependency requiring role = "admin"
require_admin = require_roles("admin")

# Helper to run module backup/restore

def run_py_module(mod: str, args: list[str]) -> tuple[int, str, str]:
    """
    Run 'python -m <mod> <args...>' and get stdout/stderr.
    Use to call app.backup / app.restore as a child script.
    """
    cmd = [sys.executable, "-m", mod, *args]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return (
        proc.returncode,
        proc.stdout.decode("utf-8", "ignore"),
        proc.stderr.decode("utf-8", "ignore"),
    )


# Schemas

class RestoreReq(BaseModel):
    """
    Payload for API restore:
    - file: path to .sql.gz file (if None -> get latest version)
    - drop_schema: if True, delete public schema before restore
    """
    file: Optional[str] = None
    drop_schema: bool = False


class BackupFile(BaseModel):
    """
    Meta information of a backup file
    """
    name: str
    path: str
    size_bytes: int
    modified_at: datetime
    created_at: datetime | None = None


class BackupListResp(BaseModel):
    """
    Results returned when listing backups
    """
    backup_dir: str
    count: int
    items: list[BackupFile]


# Endpoints

@router.post(
    "/backup-now",
    summary="Trigger immediate database backup (admin only)",
)
def backup_now(current_admin: User = Depends(require_admin)):
    """
    Run backup immediately:
        - Call module 'app.backup' using subprocess
        - Then find the latest .sql.gz file in BACKUP_DIR and return it
    """
    code, out, err = run_py_module("app.backup", [])

    backup_dir = Path(os.getenv("BACKUP_DIR", "./backups")).resolve()
    latest = None
    if backup_dir.exists():
        files = sorted(
            backup_dir.glob("*.sql.gz"),
            key=lambda p: p.name,
            reverse=True,
        )
        latest = str(files[0]) if files else None

    return {
        "ok": code == 0,
        "exit_code": code,
        "latest_file": latest,
        "stdout": out.strip(),
        "stderr": err.strip(),
    }


@router.post(
    "/restore-latest",
    summary="Restore database from latest (or given) backup (admin only)",
)
def restore_latest(
    req: RestoreReq,
    current_admin: User = Depends(require_admin),
):
    """
    Restore data from backup:
        - If req.file does not exist -> select the latest .sql.gz file in BACKUP_DIR
        - If drop_schema=True -> add flag --drop-schema to script delete public schema
        - Always add --yes so restore script does not ask for confirmation
    """
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


@router.get(
    "/backups",
    response_model=BackupListResp,
    summary="List available backup files (admin only)",
)
def list_backups(
    current_admin: User = Depends(require_admin),
    sort: str = Query(
        "name",
        regex="^(name|mtime)$",
        description="Sort by 'name' or 'mtime'",
    ),
    order: str = Query("desc", regex="^(asc|desc)$"),
    limit: int = Query(100, ge=1, le=1000),
):
    """
    List backup files in BACKUP_DIR (default ./backups):
        - Allows sorting by name or mtime
        - Has asc/desc order
        - Limits the number of returned files by limit
    """
    backup_dir = Path(os.getenv("BACKUP_DIR", "./backups")).resolve()
    backup_dir.mkdir(parents=True, exist_ok=True)

    files = list(backup_dir.glob("*.sql.gz"))

    if sort == "mtime":
        keyfunc = lambda p: p.stat().st_mtime
    else:
        keyfunc = lambda p: p.name

    reverse = order.lower() == "desc"
    files_sorted = sorted(files, key=keyfunc, reverse=reverse)

    items: list[BackupFile] = []
    for p in files_sorted[:limit]:
        st = p.stat()
        items.append(
            BackupFile(
                name=p.name,
                path=str(p),
                size_bytes=st.st_size,
                modified_at=datetime.fromtimestamp(st.st_mtime),
                created_at=(
                    datetime.fromtimestamp(st.st_ctime)
                    if st.st_ctime
                    else None
                ),
            )
        )

    return BackupListResp(
        backup_dir=str(backup_dir),
        count=len(files),
        items=items,
    )