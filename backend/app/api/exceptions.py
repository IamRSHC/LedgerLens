import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.schemas import ResolveRequest
from app.agent.investigator import investigate
import app.repository.repository as repo
import json

router = APIRouter(prefix="/api/exceptions", tags=["exceptions"])

@router.get("")
def list_exceptions(run_id: str=None, status: str=None, skip: int=0, limit: int=100,
                    db: Session=Depends(get_db)):
    excs = repo.get_exceptions(db, run_id, status, skip, limit)
    result = []
    for e in excs:
        d = {c.name: getattr(e, c.name) for c in e.__table__.columns}
        if e.investigation:
            inv = e.investigation
            d["investigation"] = {c.name: getattr(inv, c.name) for c in inv.__table__.columns}
        result.append(d)
    return result

@router.get("/{exception_id}")
def get_exception(exception_id: str, db: Session=Depends(get_db)):
    exc = repo.get_exception(db, exception_id)
    if not exc: raise HTTPException(404, "Exception not found")
    d = {c.name: getattr(exc, c.name) for c in exc.__table__.columns}
    if exc.investigation:
        inv = exc.investigation
        d["investigation"] = {c.name: getattr(inv, c.name) for c in inv.__table__.columns}
    return d

@router.post("/{exception_id}/investigate")
def reinvestigate(exception_id: str, db: Session=Depends(get_db)):
    exc = repo.get_exception(db, exception_id)
    if not exc: raise HTTPException(404, "Exception not found")
    exc_dict = {c.name: getattr(exc, c.name) for c in exc.__table__.columns}
    inv = investigate(exc_dict, db)
    existing = repo.get_investigation(db, exception_id)
    if not existing:
        repo.save_investigation(db, {"exception_id": exception_id, **inv,
            "evidence": json.dumps(inv.get("evidence",[])), "tool_calls": inv.get("tool_calls","[]")})
    return inv

@router.post("/{exception_id}/resolve")
def resolve(exception_id: str, req: ResolveRequest, db: Session=Depends(get_db)):
    exc = repo.get_exception(db, exception_id)
    if not exc: raise HTTPException(404, "Exception not found")
    repo.resolve_exception(db, exception_id, "resolved", req.resolution, req.actor)
    repo.log_action(db, exc.run_id, "exception", exception_id, "resolved", actor=req.actor)
    return {"status": "resolved", "exception_id": exception_id}
