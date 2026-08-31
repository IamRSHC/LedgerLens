from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import create_tables
from app.api import reconciliation, transactions, exceptions, audit

app = FastAPI(
    title="LedgerLens API",
    description="AI Finance Controller — Reconcile. Investigate. Resolve.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(reconciliation.router)
app.include_router(transactions.router)
app.include_router(exceptions.router)
app.include_router(audit.router)

@app.on_event("startup")
def startup():
    create_tables()
    print("[ok] LedgerLens API running")
    print("   Docs: http://localhost:8000/docs")

@app.get("/")
def root():
    return {"app": "LedgerLens", "version": "1.0.0", "status": "running"}

@app.get("/health")
def health():
    return {"status": "ok"}
