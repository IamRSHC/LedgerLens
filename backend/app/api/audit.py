from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
import app.repository.repository as repo

router = APIRouter(prefix="/api/audit", tags=["audit"])

@router.get("")
def get_audit(run_id: str=None, skip: int=0, limit: int=200, db: Session=Depends(get_db)):
    logs = repo.get_audit_logs(db, run_id, skip, limit)
    return [{c.name: getattr(l, c.name) for c in l.__table__.columns} for l in logs]
