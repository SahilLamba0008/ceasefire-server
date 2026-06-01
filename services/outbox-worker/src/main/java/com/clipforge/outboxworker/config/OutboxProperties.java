package com.clipforge.outboxworker.config;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.context.properties.bind.ConstructorBinding;

@ConfigurationProperties(prefix = "outbox")
public class OutboxProperties {

    private final int batchSize;
    private final long pollIntervalMs;
    private final long staleLeasetimeoutSeconds;
    private final int maxStartupRetries;
    private final String exchange;
    private final long publisherConfirmTimeoutMs;

    @ConstructorBinding
    public OutboxProperties(int batchSize, long pollIntervalMs, long staleLeasetimeoutSeconds,
                            int maxStartupRetries, String exchange, long publisherConfirmTimeoutMs) {
        this.batchSize = batchSize;
        this.pollIntervalMs = pollIntervalMs;
        this.staleLeasetimeoutSeconds = staleLeasetimeoutSeconds;
        this.maxStartupRetries = maxStartupRetries;
        this.exchange = exchange;
        this.publisherConfirmTimeoutMs = publisherConfirmTimeoutMs;
    }

    public int getBatchSize() { return batchSize; }
    public long getPollIntervalMs() { return pollIntervalMs; }
    public long getStaleLeasetimeoutSeconds() { return staleLeasetimeoutSeconds; }
    public int getMaxStartupRetries() { return maxStartupRetries; }
    public String getExchange() { return exchange; }
    public long getPublisherConfirmTimeoutMs() { return publisherConfirmTimeoutMs; }
}
