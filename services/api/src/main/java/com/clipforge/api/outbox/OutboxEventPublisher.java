package com.clipforge.api.outbox;

public abstract class OutboxEventPublisher {
    protected static final int INITIAL_RETRY_COUNT = 0;
    protected static final int DEFAULT_MAX_RETRIES = 5;
}
