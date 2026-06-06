package com.clipforge.outboxworker.model;

import java.time.OffsetDateTime;
import java.util.UUID;

public interface IOutboxEvent {
    UUID getId();
    String getEventType();
    String getPayload();
    OffsetDateTime getCreatedAt();
    int getRetryCount();
    int getMaxRetries();
}
