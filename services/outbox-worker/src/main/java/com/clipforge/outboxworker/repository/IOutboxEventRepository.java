package com.clipforge.outboxworker.repository;

import com.clipforge.outboxworker.model.IOutboxEvent;

import java.util.List;
import java.util.UUID;

public interface IOutboxEventRepository<T extends IOutboxEvent> {
    List<T> pollEvents(int batchSize, String workerId);
    void markProcessed(UUID eventId);
    void markFailed(UUID eventId, int retryCount, String error);
    void reschedule(UUID eventId, int retryCount, long backoffSeconds, String error);
    void releaseStaleLeases(long timeoutSeconds);
}
