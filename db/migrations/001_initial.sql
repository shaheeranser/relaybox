-- Relaybox initial schema.

CREATE TABLE subscriptions (
    id          UUID PRIMARY KEY,
    url         TEXT NOT NULL,
    secret      TEXT NOT NULL,
    event_types TEXT[] NOT NULL,
    active      BOOLEAN NOT NULL DEFAULT true,
    description TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE events (
    id              UUID PRIMARY KEY,
    type            TEXT NOT NULL,
    payload         JSONB NOT NULL,
    idempotency_key TEXT UNIQUE,
    received_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE deliveries (
    id              UUID PRIMARY KEY,
    event_id        UUID NOT NULL REFERENCES events(id),
    subscription_id UUID NOT NULL REFERENCES subscriptions(id),
    status          TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending', 'delivering', 'succeeded', 'failed', 'dead')),
    attempts        INTEGER NOT NULL DEFAULT 0,
    next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    locked_until    TIMESTAMPTZ,
    last_error      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE delivery_attempts (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    delivery_id UUID NOT NULL REFERENCES deliveries(id),
    attempt_no  INTEGER NOT NULL,
    status_code INTEGER,
    error       TEXT,
    duration_ms INTEGER,
    started_at  TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ,
    UNIQUE (delivery_id, attempt_no)
);

CREATE INDEX idx_deliveries_claimable
    ON deliveries (next_attempt_at)
    WHERE status IN ('pending', 'failed')
      AND (locked_until IS NULL OR locked_until < now());

CREATE INDEX idx_deliveries_event ON deliveries (event_id);
CREATE INDEX idx_deliveries_subscription ON deliveries (subscription_id);
CREATE INDEX idx_deliveries_status ON deliveries (status);
CREATE INDEX idx_delivery_attempts_delivery ON delivery_attempts (delivery_id);
