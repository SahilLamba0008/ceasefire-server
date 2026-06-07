CREATE TABLE IF NOT EXISTS segments (
    segment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    job_id UUID NOT NULL,

    segment_start_time TIMESTAMPTZ NOT NULL,

    segment_end_time TIMESTAMPTZ NOT NULL,

    reason VARCHAR(255) NOT NULL,

    CONSTRAINT fk_segments_jobs
        FOREIGN KEY (job_id)
        REFERENCES jobs(job_id),

    CONSTRAINT check_segment_time_order
        CHECK (segment_start_time < segment_end_time)
);