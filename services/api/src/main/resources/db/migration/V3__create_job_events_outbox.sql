CREATE SCHEMA IF NOT EXISTS events;

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


DROP TRIGGER IF EXISTS trg_jobs_set_updated_at ON jobs;

CREATE TRIGGER trg_jobs_set_updated_at
BEFORE UPDATE ON jobs
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();


CREATE TABLE IF NOT EXISTS events.job_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    job_id UUID NOT NULL
        REFERENCES jobs(job_id)
        ON DELETE RESTRICT,

    event_type VARCHAR(100) NOT NULL,

    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',

    payload JSONB NOT NULL,

    retry_count INTEGER NOT NULL DEFAULT 0,

    max_retries INTEGER NOT NULL DEFAULT 5,

    locked_by VARCHAR(100) NOT NULL,

    locked_at TIMESTAMPTZ,

    available_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    processed_at TIMESTAMPTZ,

    last_error TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT job_events_status_check
        CHECK (
            status IN (
                'PENDING',
                'PROCESSING',
                'PROCESSED',
                'FAILED'
            )
        ),

    CONSTRAINT job_events_retry_count_check
        CHECK (retry_count >= 0),

    CONSTRAINT job_events_max_retries_check
        CHECK (max_retries >= 0)
);


CREATE INDEX IF NOT EXISTS idx_job_events_status_available_created
ON events.job_events (
    status,
    available_at,
    created_at
);

CREATE INDEX IF NOT EXISTS idx_job_events_job_id
ON events.job_events (job_id);

CREATE INDEX IF NOT EXISTS idx_job_events_event_type_status
ON events.job_events (
    event_type,
    status
);


DROP TRIGGER IF EXISTS trg_job_events_set_updated_at
ON events.job_events;

CREATE TRIGGER trg_job_events_set_updated_at
BEFORE UPDATE ON events.job_events
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP FUNCTION IF EXISTS jobs_set_updated_at();

CREATE OR REPLACE FUNCTION events.poll_job_events(
    p_batch_size INTEGER,
    p_locked_by VARCHAR
)
RETURNS SETOF events.job_events
LANGUAGE plpgsql
AS $$
BEGIN
    IF p_batch_size IS NULL OR p_batch_size <= 0 THEN
        RETURN;
    END IF;

    RETURN QUERY
    WITH candidate_events AS (
        SELECT je.id
        FROM events.job_events AS je
        WHERE je.status = 'PENDING'
          AND je.available_at <= now()
        ORDER BY je.created_at ASC
        FOR UPDATE SKIP LOCKED
        LIMIT p_batch_size
    ),
    claimed_events AS (
        UPDATE events.job_events AS je
        SET status = 'PROCESSING',
            locked_by = p_locked_by,
            locked_at = now()
        FROM candidate_events AS ce
        WHERE je.id = ce.id
        RETURNING je.*
    )
    SELECT *
    FROM claimed_events
    ORDER BY created_at ASC;
END;
$$;