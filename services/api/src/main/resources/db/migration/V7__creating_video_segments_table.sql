CREATE TABLE IF NOT EXISTS segments (
    segment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL,
    segment_start_time NUMERIC(10,2) NOT NULL,
    segment_end_time NUMERIC(10,2) NOT NULL,
    reason TEXT NOT NULL,

    CONSTRAINT fk_segments_jobs
        FOREIGN KEY(job_id)
        REFERENCES jobs(job_id),
        
    CONSTRAINT check_segment_time_order
        CHECK(
            segment_start_time < segment_end_time
        )
);