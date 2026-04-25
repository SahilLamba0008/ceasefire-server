ALTER TABLE events.job_events
    ALTER COLUMN locked_by DROP NOT NULL;

ALTER TABLE events.job_events
    ADD CONSTRAINT job_events_lock_owner_check
        CHECK (
            (status = 'PROCESSING' AND locked_by IS NOT NULL AND locked_at IS NOT NULL)
            OR
            (status <> 'PROCESSING' AND locked_by IS NULL AND locked_at IS NULL)
        );
