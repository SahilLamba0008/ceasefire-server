DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'jobs'
          AND column_name = 'id'
    ) THEN
        ALTER TABLE public.jobs RENAME COLUMN id TO job_id;
    END IF;
END
$$;

ALTER TABLE public.jobs
    ADD COLUMN IF NOT EXISTS title TEXT,
    ADD COLUMN IF NOT EXISTS description TEXT,
    ADD COLUMN IF NOT EXISTS youtube_url TEXT;

UPDATE public.jobs
SET title = COALESCE(title, 'Untitled'),
    description = COALESCE(description, ''),
    youtube_url = COALESCE(youtube_url, '')
WHERE title IS NULL OR description IS NULL OR youtube_url IS NULL;

ALTER TABLE public.jobs
    ALTER COLUMN title SET NOT NULL,
    ALTER COLUMN description SET NOT NULL,
    ALTER COLUMN youtube_url SET NOT NULL;

CREATE OR REPLACE FUNCTION public.jobs_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_jobs_set_updated_at ON public.jobs;

CREATE TRIGGER trg_jobs_set_updated_at
BEFORE UPDATE ON public.jobs
FOR EACH ROW
EXECUTE FUNCTION public.jobs_set_updated_at();
