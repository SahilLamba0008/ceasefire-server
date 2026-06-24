CREATE TABLE IF NOT EXISTS clips (
    clip_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    segment_id    UUID NOT NULL REFERENCES segments(segment_id),
    job_id        UUID NOT NULL REFERENCES jobs(job_id),
    status        VARCHAR(20) NOT NULL DEFAULT 'pending',
    output_key    TEXT,
    thumbnail_key TEXT,
    last_error    TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT check_clip_status CHECK (status IN ('pending', 'rendering', 'rendered', 'failed'))
);

CREATE INDEX idx_clips_job ON clips(job_id);
CREATE INDEX idx_clips_segment ON clips(segment_id);

DROP TRIGGER IF EXISTS trg_clips_set_updated_at ON clips;

CREATE TRIGGER trg_clips_set_updated_at
BEFORE UPDATE ON clips
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();
