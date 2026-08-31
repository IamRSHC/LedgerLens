from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.schemas import ResolveRequest, FlagRequest
from app.agent.investigator import investigate
import app.repository.repository as repo
import json

router = APIRouter(prefix="/api/exceptions", tags=["exceptions"])


def _serialize(exc) -> dict:
    d = {c.name: getattr(exc, c.name) for c in exc.__table__.columns}
    if exc.investigation:
        inv = exc.investigation
        d["investigation"] = {c.name: getattr(inv, c.name) for c in inv.__table__.columns}
    return d


@router.get("")
def list_exceptions(run_id: str=None, status: str=None, skip: int=0, limit: int=100,
                    db: Session=Depends(get_db)):
    excs = repo.get_exceptions(db, run_id, status, skip, limit)
    return [_serialize(e) for e in excs]


@router.get("/{exception_id}")
def get_exception(exception_id: str, db: Session=Depends(get_db)):
    exc = repo.get_exception(db, exception_id)
    if not exc: raise HTTPException(404, "Exception not found")
    return _serialize(exc)


@router.post("/{exception_id}/investigate")
def reinvestigate(exception_id: str, db: Session=Depends(get_db)):
    """Re-run the investigator on an exception.

    Terminal exceptions (auto_resolved / resolved) are treated as immutable — the
    existing investigation (if any) is returned unchanged rather than overwritten.
    """
    exc = repo.get_exception(db, exception_id)
    if not exc: raise HTTPException(404, "Exception not found")

    if exc.status in repo.TERMINAL_STATUSES:
        existing = repo.get_investigation(db, exception_id)
        if existing:
            return {c.name: getattr(existing, c.name) for c in existing.__table__.columns}
        raise HTTPException(
            409,
            f"Cannot re-investigate exception in terminal status {exc.status!r} "
            "with no existing investigation.",
        )

    exc_dict = {c.name: getattr(exc, c.name) for c in exc.__table__.columns}
    inv = investigate(exc_dict, db)
    existing = repo.get_investigation(db, exception_id)
    if not existing:
        repo.save_investigation(db, {"exception_id": exception_id, **inv,
            "evidence": json.dumps(inv.get("evidence",[])), "tool_calls": inv.get("tool_calls","[]")})
    return inv


@router.post("/{exception_id}/resolve")
def resolve(exception_id: str, req: ResolveRequest, db: Session=Depends(get_db)):
    """Mark an exception resolved.

    Allowed transitions (from repo.ALLOWED_TRANSITIONS):
      open           → resolved
      manual_review  → resolved
    Already-resolved / auto-resolved exceptions are treated idempotently.
    """
    exc = repo.get_exception(db, exception_id)
    if not exc: raise HTTPException(404, "Exception not found")

    if exc.status in repo.TERMINAL_STATUSES:
        return {"status": exc.status, "exception_id": exception_id, "idempotent": True}

    try:
        updated = repo.transition_exception(
            db, exception_id, repo.STATUS_RESOLVED,
            actor=req.actor, resolution=req.resolution, action="resolved",
        )
    except repo.InvalidTransition as e:
        raise HTTPException(409, detail=str(e))
    return {"status": updated.status, "exception_id": exception_id}


@router.post("/{exception_id}/flag")
def flag_for_review(exception_id: str, req: FlagRequest = FlagRequest(), db: Session=Depends(get_db)):
    """Move an exception into `manual_review` — the state the user reviews later.

    Distinct from `/resolve`: flagging does NOT close the exception, it hands it
    to a human. Rejecting `auto_resolved` cases (the AI already closed them) is
    intentional; already-`manual_review` items are idempotent.
    """
    exc = repo.get_exception(db, exception_id)
    if not exc: raise HTTPException(404, "Exception not found")

    if exc.status == repo.STATUS_MANUAL_REVIEW:
        return {"status": exc.status, "exception_id": exception_id, "idempotent": True}

    try:
        updated = repo.transition_exception(
            db, exception_id, repo.STATUS_MANUAL_REVIEW,
            actor=req.actor, resolution=req.reason,
            action="flagged_for_manual_review",
        )
    except repo.InvalidTransition as e:
        raise HTTPException(409, detail=str(e))
    return {"status": updated.status, "exception_id": exception_id}
