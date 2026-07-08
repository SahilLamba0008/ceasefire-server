package com.clipforge.outboxworker.service;

import com.clipforge.outboxworker.config.OutboxProperties;
import com.clipforge.outboxworker.logging.OutboxMdc;
import com.clipforge.outboxworker.model.IOutboxEvent;
import com.clipforge.outboxworker.publisher.IEventPublisher;
import com.clipforge.outboxworker.repository.IOutboxEventRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.amqp.AmqpException;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.context.SmartLifecycle;
import org.springframework.dao.DataAccessException;

import java.net.InetAddress;
import java.net.UnknownHostException;
import java.util.List;
import java.util.UUID;

public abstract class OutboxPollingService<T extends IOutboxEvent> implements SmartLifecycle {

    protected static final Logger log = LoggerFactory.getLogger(OutboxPollingService.class);

    private final RabbitTemplate rabbit;
    private final IEventPublisher<T> publisher;
    private final IOutboxEventRepository<T> repository;
    private final OutboxProperties props;
    private final String workerId;

    private volatile boolean running = false;
    private Thread pollingThread;

    protected OutboxPollingService(RabbitTemplate rabbit, IEventPublisher<T> publisher,
                                   IOutboxEventRepository<T> repository, OutboxProperties props) {
        this.rabbit = rabbit;
        this.publisher = publisher;
        this.repository = repository;
        this.props = props;
        this.workerId = buildWorkerId();
    }

    @Override
    public void start() {
        running = true;
        pollingThread = new Thread(this::runPollingLoop, threadName());
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

    protected abstract String threadName();

    private void runPollingLoop() {
        waitForRabbitMQ();
        log.info("Outbox worker ready [workerId={}]", workerId);

        while (running) {
            try {
                repository.releaseStaleLeases(props.getStaleLeasetimeoutSeconds());
                List<T> events = repository.pollEvents(props.getBatchSize(), workerId);
                for (T event : events) {
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

    private void processEvent(T event) {
        try {
            OutboxMdc.putEventContext(event);
            publisher.publish(event, props.getExchange());
            repository.markProcessed(event.getId());
            log.info("Event marked PROCESSED [event_id={}, event_type={}]", event.getId(), event.getEventType());
        } catch (AmqpException | DataAccessException e) {
            handleFailure(event, e);
        } finally {
            OutboxMdc.clear();
        }
    }

    private void handleFailure(T event, Exception e) {
        int nextRetryCount = event.getRetryCount() + 1;
        String errorMsg = OutboxMdc.truncate(e.getMessage(), 1000);

        if (nextRetryCount >= event.getMaxRetries()) {
            repository.markDead(event.getId(), nextRetryCount, errorMsg);
            log.error("Event moved to DEAD [event_id={}, retries={}]: {}",
                event.getId(), nextRetryCount, errorMsg);
        } else {
            long backoffSeconds = (long) Math.pow(2, nextRetryCount);
            repository.reschedule(event.getId(), nextRetryCount, backoffSeconds, errorMsg);
            log.warn("Publish failed [event_id={}, retry={}/{}] scheduled in {}s: {}",
                event.getId(), nextRetryCount, event.getMaxRetries(), backoffSeconds, errorMsg);
        }
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
