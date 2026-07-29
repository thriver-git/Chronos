CREATE TABLE IF NOT EXISTS audit_events (
    id BIGSERIAL PRIMARY KEY,
    occurred_at TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    event_type TEXT NOT NULL,
    message TEXT NOT NULL,
    action TEXT,
    confidence_score INTEGER,
    reasoning TEXT,
    payload JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS audit_events_occurred_at_idx ON audit_events (occurred_at DESC);
CREATE INDEX IF NOT EXISTS audit_events_symbol_occurred_at_idx ON audit_events (symbol, occurred_at DESC);

CREATE TABLE IF NOT EXISTS market_snapshots (
    id BIGSERIAL PRIMARY KEY,
    occurred_at TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    price NUMERIC(18, 6) NOT NULL,
    rsi NUMERIC(8, 4) NOT NULL,
    macd NUMERIC(18, 8) NOT NULL,
    macd_signal NUMERIC(18, 8) NOT NULL
);

CREATE TABLE IF NOT EXISTS llm_decisions (
    id BIGSERIAL PRIMARY KEY,
    market_snapshot_id BIGINT REFERENCES market_snapshots(id),
    occurred_at TIMESTAMPTZ NOT NULL,
    model_name TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    action TEXT NOT NULL,
    confidence_score INTEGER NOT NULL,
    reasoning TEXT NOT NULL,
    raw_response JSONB
);

CREATE TABLE IF NOT EXISTS risk_checks (
    id BIGSERIAL PRIMARY KEY,
    llm_decision_id BIGINT REFERENCES llm_decisions(id),
    occurred_at TIMESTAMPTZ NOT NULL,
    allowed BOOLEAN NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 0,
    reason TEXT NOT NULL,
    halt BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS broker_orders (
    id BIGSERIAL PRIMARY KEY,
    llm_decision_id BIGINT REFERENCES llm_decisions(id),
    alpaca_order_id UUID UNIQUE NOT NULL,
    submitted_at TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    quantity NUMERIC(18, 6) NOT NULL,
    limit_price NUMERIC(18, 6),
    status TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS fills (
    id BIGSERIAL PRIMARY KEY,
    broker_order_id BIGINT NOT NULL REFERENCES broker_orders(id),
    filled_at TIMESTAMPTZ NOT NULL,
    quantity NUMERIC(18, 6) NOT NULL,
    price NUMERIC(18, 6) NOT NULL,
    UNIQUE (broker_order_id, filled_at, quantity, price)
);

CREATE TABLE IF NOT EXISTS account_snapshots (
    id BIGSERIAL PRIMARY KEY,
    occurred_at TIMESTAMPTZ NOT NULL,
    equity NUMERIC(18, 6) NOT NULL,
    buying_power NUMERIC(18, 6) NOT NULL,
    unrealized_pnl NUMERIC(18, 6) NOT NULL
);

CREATE TABLE IF NOT EXISTS runtime_events (
    id BIGSERIAL PRIMARY KEY,
    occurred_at TIMESTAMPTZ NOT NULL,
    state TEXT NOT NULL,
    detail TEXT NOT NULL
);
