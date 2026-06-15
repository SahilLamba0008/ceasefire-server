-- Migration V8: add DEAD to job_events status check and migrate exhausted FAILED rows
BEGIN;

-- 1) Update status check constraint to include 'DEAD'
ALTER TABLE IF EXISTS events.job_events
    DROP CONSTRAINT IF EXISTS job_events_status_check;

ALTER TABLE IF EXISTS events.job_events
    ADD CONSTRAINT job_events_status_check
        CHECK (status IN ('PENDING','PROCESSING','PROCESSED','FAILED','DEAD'));

-- 2) Migrate existing FAILED rows that have exhausted retries to DEAD
UPDATE events.job_events
SET status = 'DEAD', updated_at = now()
WHERE status = 'FAILED'
  AND retry_count >= max_retries;

-- 3) Replace poll_job_events to also return retryable FAILED rows (but exclude DEAD)
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
        WHERE (
            je.status = 'PENDING'
            OR (je.status = 'FAILED' AND je.retry_count < je.max_retries)
        )
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

COMMIT;
