package com.clipforge.outboxworker.service;

import com.clipforge.outboxworker.config.OutboxProperties;
import com.clipforge.outboxworker.model.JobEvent;
import com.clipforge.outboxworker.model.JobEventRowMapper;
import com.clipforge.outboxworker.publisher.IEventPublisher;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.amqp.AmqpException;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.context.SmartLifecycle;
import org.springframework.dao.DataAccessException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

import java.net.InetAddress;
import java.net.UnknownHostException;
import java.util.List;
import java.util.UUID;

@Service
public class OutboxPollingService implements SmartLifecycle {

    private static final Logger log = LoggerFactory.getLogger(OutboxPollingService.class);
    private static final JobEventRowMapper ROW_MAPPER = new JobEventRowMapper();

    private final JdbcTemplate jdbc;
    private final RabbitTemplate rabbit;
    private final IEventPublisher publisher;
    private final OutboxProperties props;
    private final String workerId;

    private volatile boolean running = false;
    private Thread pollingThread;

    public OutboxPollingService(JdbcTemplate jdbc, RabbitTemplate rabbit,
                                IEventPublisher publisher, OutboxProperties props) {
        this.jdbc = jdbc;
        this.rabbit = rabbit;
        this.publisher = publisher;
        this.props = props;
        this.workerId = buildWorkerId();
    }

    @Override
    public void start() {
        running = true;
        pollingThread = new Thread(this::runLoop, "outbox-poller");
        pollingThread.setDaemon(false);
        pollingThread.start();
    }

    @Override
    public void stop() {
        stop(() -> {});
    }

    @Override
    public void stop(Runnable callback) {
        log.info("Shutting down outbox worker — finishing in-flight batch...");
        running = false;
        if (pollingThread != null) {
            try {
                pollingThread.join(30_000);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        }
        log.info("Outbox worker stopped gracefully");
        callback.run();
    }

    @Override
    public boolean isRunning() {
        return running;
    }

    private void runLoop() {
        waitForDb();
        waitForRabbitMQ();
        log.info("Outbox worker ready [workerId={}]", workerId);

        while (running) {
            try {
                releaseStaleLeases();
                List<JobEvent> events = pollEvents();
                for (JobEvent event : events) {
                    if (!running) break;
                    processEvent(event);
                }
            } catch (DataAccessException e) {
                log.warn("DB error during poll cycle, will retry: {}", e.getMessage());
            } catch (Exception e) {
                log.error("Unexpected error in poll cycle", e);
            }

            sleep(props.getPollIntervalMs());
        }
    }

    private void waitForDb() {
        waitForConnection("database", () -> jdbc.queryForObject("SELECT 1", Integer.class));
    }

    private void waitForRabbitMQ() {
        waitForConnection("RabbitMQ", () -> rabbit.getConnectionFactory().createConnection().close());
    }

    private void waitForConnection(String name, Runnable check) {
        int attempt = 0;
        while (running) {
            try {
                check.run();
                log.info("Connected to {}", name);
                return;
            } catch (Exception e) {
                attempt++;
                long backoffMs = backoff(attempt);
                log.warn("{} not ready (attempt {}), retrying in {}ms", name, attempt, backoffMs);
                sleep(backoffMs);
            }
        }
    }

    private List<JobEvent> pollEvents() {
        return jdbc.query(
            "SELECT * FROM events.poll_job_events(?, ?)",
            ROW_MAPPER,
            props.getBatchSize(),
            workerId
        );
    }

    private void processEvent(JobEvent event) {
        try {
            publisher.publish(event, props.getExchange());
            markProcessed(event.getId());
        } catch (AmqpException | DataAccessException e) {
            handleFailure(event, e);
        }
    }

    private void markProcessed(UUID eventId) {
        jdbc.update("""
            UPDATE events.job_events
            SET status = 'PROCESSED', processed_at = now(), locked_by = NULL, locked_at = NULL
            WHERE id = ?
            """, eventId);
    }

    private void handleFailure(JobEvent event, Exception e) {
        int nextRetryCount = event.getRetryCount() + 1;
        String errorMsg = truncate(e.getMessage(), 1000);

        if (nextRetryCount >= event.getMaxRetries()) {
            jdbc.update("""
                UPDATE events.job_events
                SET status = 'FAILED', retry_count = ?, last_error = ?, locked_by = NULL, locked_at = NULL
                WHERE id = ?
                """, nextRetryCount, errorMsg, event.getId());
            log.error("Event {} permanently failed after {} retries: {}", event.getId(), nextRetryCount, e.getMessage());
        } else {
            long backoffSeconds = (long) Math.pow(2, nextRetryCount);
            jdbc.update("""
                UPDATE events.job_events
                SET status = 'PENDING', retry_count = ?,
                    available_at = now() + (? * interval '1 second'),
                    last_error = ?, locked_by = NULL, locked_at = NULL
                WHERE id = ?
                """, nextRetryCount, backoffSeconds, errorMsg, event.getId());
            log.warn("Event {} failed, retry {}/{} scheduled in {}s",
                event.getId(), nextRetryCount, event.getMaxRetries(), backoffSeconds);
        }
    }

    private void releaseStaleLeases() {
        int reset = jdbc.update("""
            UPDATE events.job_events
            SET status = 'PENDING', locked_by = NULL, locked_at = NULL
            WHERE status = 'PROCESSING'
              AND locked_at < now() - (? * interval '1 second')
              AND retry_count < max_retries
            """, props.getStaleLeasetimeoutSeconds());

        int failed = jdbc.update("""
            UPDATE events.job_events
            SET status = 'FAILED', locked_by = NULL, locked_at = NULL,
                last_error = 'Stale lease: processing timed out'
            WHERE status = 'PROCESSING'
              AND locked_at < now() - (? * interval '1 second')
              AND retry_count >= max_retries
            """, props.getStaleLeasetimeoutSeconds());

        if (reset > 0) log.info("Released {} stale lease(s) back to PENDING", reset);
        if (failed > 0) log.warn("Marked {} stale lease(s) as FAILED (max retries exhausted)", failed);
    }

    private long backoff(int attempt) {
        return Math.min(30_000L, (long) Math.pow(2, Math.min(attempt, 10)) * 1_000L);
    }

    private void sleep(long ms) {
        try {
            Thread.sleep(ms);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }

    private String truncate(String s, int max) {
        if (s == null) return null;
        return s.length() <= max ? s : s.substring(0, max);
    }

    private String buildWorkerId() {
        String host;
        try {
            host = InetAddress.getLocalHost().getHostName();
        } catch (UnknownHostException e) {
            host = "unknown";
        }
        return host + "-" + UUID.randomUUID().toString().substring(0, 8);
    }
}
