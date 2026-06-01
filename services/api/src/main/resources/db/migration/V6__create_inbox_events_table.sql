CREATE SCHEMA IF NOT EXISTS events;

CREATE TABLE IF NOT EXISTS events.inbox_events (
    message_id UUID PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
