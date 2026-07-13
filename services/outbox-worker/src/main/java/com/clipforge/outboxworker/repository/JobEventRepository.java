package com.clipforge.outboxworker.repository;

import com.clipforge.outboxworker.logging.OutboxMdc;
import com.clipforge.outboxworker.model.JobEvent;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.core.namedparam.MapSqlParameterSource;
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;
import org.springframework.stereotype.Repository;

import java.sql.Timestamp;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

@Repository
public class JobEventRepository implements IOutboxEventRepository<JobEvent> {

    private static final Logger log = LoggerFactory.getLogger(JobEventRepository.class);

    private static final RowMapper<JobEvent> ROW_MAPPER = (rs, rowNum) -> {
        JobEvent event = new JobEvent();
        event.setId(rs.getObject("id", UUID.class));
        event.setEventType(rs.getString("event_type"));
        event.setPayload(rs.getString("payload"));
        event.setRetryCount(rs.getInt("retry_count"));
        event.setMaxRetries(rs.getInt("max_retries"));
        event.setCreatedAt(toOffsetDateTime(rs.getTimestamp("created_at")));
        return event;
    };

    private final NamedParameterJdbcTemplate jdbc;

    public JobEventRepository(NamedParameterJdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    @Override
    public List<JobEvent> pollEvents(int batchSize, String workerId) {
        return jdbc.query(
            "SELECT * FROM events.poll_job_events(:batchSize, :workerId)",
            new MapSqlParameterSource()
                .addValue("batchSize", batchSize)
                .addValue("workerId", workerId),
            ROW_MAPPER
        );
    }

    @Override
    public void markProcessed(UUID eventId) {
        jdbc.update("""
            UPDATE events.job_events
            SET status = 'PROCESSED', processed_at = now(), locked_by = NULL, locked_at = NULL
            WHERE id = :id
            """,
            new MapSqlParameterSource("id", eventId)
        );
    }

    @Override
    public void markDead(UUID eventId, int retryCount, String error) {
        jdbc.update("""
            UPDATE events.job_events
            SET status = 'DEAD', retry_count = :retryCount, last_error = :error,
                locked_by = NULL, locked_at = NULL, updated_at = now()
            WHERE id = :id
            """,
            new MapSqlParameterSource()
                .addValue("retryCount", retryCount)
                .addValue("error", error)
                .addValue("id", eventId)
        );
    }

    @Override
    public void reschedule(UUID eventId, int retryCount, long backoffSeconds, String error) {
        jdbc.update("""
            UPDATE events.job_events
            SET status = 'PENDING', retry_count = :retryCount,
                available_at = now() + (:backoffSeconds * interval '1 second'),
                last_error = :error, locked_by = NULL, locked_at = NULL
            WHERE id = :id
            """,
            new MapSqlParameterSource()
                .addValue("retryCount", retryCount)
                .addValue("backoffSeconds", backoffSeconds)
                .addValue("error", error)
                .addValue("id", eventId)
        );
    }

    @Override
    public void releaseStaleLeases(long timeoutSeconds) {
        List<RecoveredLease> resetLeases = recoverStaleLeases("""
            SELECT id, job_id, EXTRACT(EPOCH FROM (now() - locked_at))::bigint AS lease_age_seconds
            FROM events.job_events
            WHERE status = 'PROCESSING'
              AND locked_at < now() - make_interval(secs => :timeoutSeconds)
              AND retry_count < max_retries
            """, timeoutSeconds);

        List<RecoveredLease> deadLeases = recoverStaleLeases("""
            SELECT id, job_id, EXTRACT(EPOCH FROM (now() - locked_at))::bigint AS lease_age_seconds
            FROM events.job_events
            WHERE status = 'PROCESSING'
              AND locked_at < now() - make_interval(secs => :timeoutSeconds)
              AND retry_count >= max_retries
            """, timeoutSeconds);

        for (RecoveredLease lease : resetLeases) {
            jdbc.update("""
                UPDATE events.job_events
                SET status = 'PENDING', locked_by = NULL, locked_at = NULL, updated_at = now()
                WHERE id = :id
                  AND status = 'PROCESSING'
                  AND locked_at < now() - make_interval(secs => :timeoutSeconds)
                  AND retry_count < max_retries
                """,
                new MapSqlParameterSource()
                    .addValue("id", lease.eventId())
                    .addValue("timeoutSeconds", timeoutSeconds)
            );

            OutboxMdc.putEventContext(lease.eventId(), lease.jobId());
            try {
                log.warn("Released stale lease back to PENDING [event_id={}, lease_age_seconds={}s]",
                    lease.eventId(), lease.leaseAgeSeconds());
            } finally {
                OutboxMdc.clear();
            }
        }

        for (RecoveredLease lease : deadLeases) {
            jdbc.update("""
                UPDATE events.job_events
                SET status = 'DEAD', locked_by = NULL, locked_at = NULL,
                    last_error = 'Stale lease: processing timed out', updated_at = now()
                WHERE id = :id
                  AND status = 'PROCESSING'
                  AND locked_at < now() - make_interval(secs => :timeoutSeconds)
                  AND retry_count >= max_retries
                """,
                new MapSqlParameterSource()
                    .addValue("id", lease.eventId())
                    .addValue("timeoutSeconds", timeoutSeconds)
            );

            OutboxMdc.putEventContext(lease.eventId(), lease.jobId());
            try {
                log.error("Moved stale lease to DEAD [event_id={}, lease_age_seconds={}s, reason=max_retries_exhausted]",
                    lease.eventId(), lease.leaseAgeSeconds());
            } finally {
                OutboxMdc.clear();
            }
        }
    }

    private static OffsetDateTime toOffsetDateTime(Timestamp ts) {
        if (ts == null) return null;
        return ts.toInstant().atOffset(ZoneOffset.UTC);
    }

    private List<RecoveredLease> recoverStaleLeases(String sql, long timeoutSeconds) {
        return jdbc.query(sql, new MapSqlParameterSource("timeoutSeconds", timeoutSeconds), rs -> {
            List<RecoveredLease> recoveredLeases = new ArrayList<>();
            while (rs.next()) {
                recoveredLeases.add(new RecoveredLease(
                    rs.getObject("id", UUID.class),
                    rs.getObject("job_id", UUID.class),
                    rs.getLong("lease_age_seconds")
                ));
            }
            return recoveredLeases;
        });
    }

    private record RecoveredLease(UUID eventId, UUID jobId, long leaseAgeSeconds) {
    }
}
