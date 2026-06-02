package com.clipforge.outboxworker.repository;

import com.clipforge.outboxworker.model.JobEvent;
import com.clipforge.outboxworker.model.JobEventRowMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.UUID;

@Repository
public class JobEventRepository implements IOutboxEventRepository<JobEvent> {

    private static final Logger log = LoggerFactory.getLogger(JobEventRepository.class);
    private static final JobEventRowMapper ROW_MAPPER = new JobEventRowMapper();

    private final JdbcTemplate jdbc;

    public JobEventRepository(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    @Override
    public List<JobEvent> pollEvents(int batchSize, String workerId) {
        return jdbc.query(
            "SELECT * FROM events.poll_job_events(?, ?)",
            ROW_MAPPER,
            batchSize,
            workerId
        );
    }

    @Override
    public void markProcessed(UUID eventId) {
        jdbc.update("""
            UPDATE events.job_events
            SET status = 'PROCESSED', processed_at = now(), locked_by = NULL, locked_at = NULL
            WHERE id = ?
            """, eventId);
    }

    @Override
    public void markFailed(UUID eventId, int retryCount, String error) {
        jdbc.update("""
            UPDATE events.job_events
            SET status = 'FAILED', retry_count = ?, last_error = ?, locked_by = NULL, locked_at = NULL
            WHERE id = ?
            """, retryCount, error, eventId);
    }

    @Override
    public void reschedule(UUID eventId, int retryCount, long backoffSeconds, String error) {
        jdbc.update("""
            UPDATE events.job_events
            SET status = 'PENDING', retry_count = ?,
                available_at = now() + (? * interval '1 second'),
                last_error = ?, locked_by = NULL, locked_at = NULL
            WHERE id = ?
            """, retryCount, backoffSeconds, error, eventId);
    }

    @Override
    public void releaseStaleLeases(long timeoutSeconds) {
        int reset = jdbc.update("""
            UPDATE events.job_events
            SET status = 'PENDING', locked_by = NULL, locked_at = NULL
            WHERE status = 'PROCESSING'
              AND locked_at < now() - (? * interval '1 second')
              AND retry_count < max_retries
            """, timeoutSeconds);

        int failed = jdbc.update("""
            UPDATE events.job_events
            SET status = 'FAILED', locked_by = NULL, locked_at = NULL,
                last_error = 'Stale lease: processing timed out'
            WHERE status = 'PROCESSING'
              AND locked_at < now() - (? * interval '1 second')
              AND retry_count >= max_retries
            """, timeoutSeconds);

        if (reset > 0) log.info("Released {} stale lease(s) back to PENDING", reset);
        if (failed > 0) log.warn("Marked {} stale lease(s) as FAILED (max retries exhausted)", failed);
    }
}
