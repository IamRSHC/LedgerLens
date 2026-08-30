from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
import app.repository.repository as repo

router = APIRouter(prefix="/api/transactions", tags=["transactions"])

@router.get("/orders")
def list_orders(skip: int=0, limit: int=50, db: Session=Depends(get_db)):
    return repo.get_orders(db, skip, limit)

@router.get("/settlements")
def list_settlements(skip: int=0, limit: int=50, db: Session=Depends(get_db)):
    return repo.get_settlements(db, skip, limit)

@router.get("/bank")
def list_bank(skip: int=0, limit: int=50, db: Session=Depends(get_db)):
    return repo.get_bank_txns(db, skip, limit)
