package com.clipforge.outboxworker.publisher;

import com.clipforge.outboxworker.model.IOutboxEvent;

public interface IEventPublisher<T extends IOutboxEvent> {
    void publish(T event, String exchange);
}
