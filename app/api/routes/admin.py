# app/api/routes/admin.py
from fastapi import APIRouter, Depends
from app.core.permission import require_roles

router = APIRouter(prefix="/admin")

@router.post("/rebuild-index")
def rebuild_index(_=Depends(require_roles("admin"))):
    return {"status": "ok"}
