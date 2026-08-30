-- LedgerLens — Supabase PostgreSQL Schema
-- Run this in: Supabase Dashboard → SQL Editor → New Query

CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    order_id TEXT UNIQUE NOT NULL,
    merchant_id TEXT,
    customer_id TEXT,
    amount FLOAT NOT NULL,
    currency TEXT DEFAULT 'INR',
    status TEXT,
    payment_method TEXT,
    created_at TIMESTAMPTZ,
    reference_id TEXT
);

CREATE TABLE IF NOT EXISTS settlements (
    id SERIAL PRIMARY KEY,
    settlement_id TEXT UNIQUE NOT NULL,
    order_id TEXT,
    merchant_id TEXT,
    gross_amount FLOAT,
    fee FLOAT,
    net_amount FLOAT,
    utr TEXT,
    status TEXT,
    settled_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS bank_transactions (
    id SERIAL PRIMARY KEY,
    bank_txn_id TEXT UNIQUE NOT NULL,
    utr TEXT,
    credit_amount FLOAT,
    debit_amount FLOAT,
    narration TEXT,
    transaction_date TIMESTAMPTZ,
    value_date TIMESTAMPTZ,
    bank TEXT
);

CREATE TABLE IF NOT EXISTS reconciliation_runs (
    id SERIAL PRIMARY KEY,
    run_id TEXT UNIQUE NOT NULL,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    total_records INT DEFAULT 0,
    matched INT DEFAULT 0,
    exceptions INT DEFAULT 0,
    match_rate FLOAT,
    amount_reconciled FLOAT DEFAULT 0,
    status TEXT DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS reconciliation_results (
    id SERIAL PRIMARY KEY,
    run_id TEXT REFERENCES reconciliation_runs(run_id),
    order_id TEXT,
    settlement_id TEXT,
    bank_txn_id TEXT,
    match_type TEXT,
    match_score FLOAT,
    status TEXT,
    amount_delta FLOAT,
    date_delta_days FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS exceptions (
    id SERIAL PRIMARY KEY,
    exception_id TEXT UNIQUE NOT NULL,
    result_id INT REFERENCES reconciliation_results(id),
    run_id TEXT,
    order_id TEXT,
    exception_type TEXT,
    severity TEXT,
    amount_delta FLOAT,
    status TEXT DEFAULT 'open',
    resolution TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS ai_investigations (
    id SERIAL PRIMARY KEY,
    exception_id TEXT UNIQUE REFERENCES exceptions(exception_id),
    root_cause TEXT,
    classification TEXT,
    confidence FLOAT,
    explanation TEXT,
    recommended_action TEXT,
    evidence TEXT,
    tool_calls TEXT,
    risk_level TEXT,
    auto_resolved BOOLEAN DEFAULT FALSE,
    investigated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    run_id TEXT,
    entity_type TEXT,
    entity_id TEXT,
    action TEXT,
    actor TEXT DEFAULT 'system',
    detail TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_orders_order_id    ON orders(order_id);
CREATE INDEX IF NOT EXISTS idx_settlements_utr    ON settlements(utr);
CREATE INDEX IF NOT EXISTS idx_bank_utr           ON bank_transactions(utr);
CREATE INDEX IF NOT EXISTS idx_exceptions_run     ON exceptions(run_id);
CREATE INDEX IF NOT EXISTS idx_audit_run          ON audit_logs(run_id);
