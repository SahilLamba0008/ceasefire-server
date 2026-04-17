-- 1. Rename id -> job_id to align with Job entity mapping
ALTER TABLE jobs RENAME COLUMN id TO job_id;

-- 2. Remove DB-side UUID default (Hibernate generates UUIDs)
ALTER TABLE jobs ALTER COLUMN job_id DROP DEFAULT;

-- 3. Add payload columns used by the API
ALTER TABLE jobs
    ADD COLUMN title TEXT NOT NULL DEFAULT 'Untitled',
    ADD COLUMN description TEXT NOT NULL DEFAULT '',
    ADD COLUMN youtube_url TEXT NOT NULL DEFAULT '';

-- 4. Normalize existing status values
UPDATE jobs SET status = UPPER(status);

-- 5. Match DB default status with backend convention
ALTER TABLE jobs
    ALTER COLUMN status SET DEFAULT 'PENDING';

-- 6. Ensure updated_at auto-updates on row updates
CREATE OR REPLACE FUNCTION jobs_set_updated_at()
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
EXECUTE FUNCTION jobs_set_updated_at();
