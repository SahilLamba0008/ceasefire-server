package com.clipforge.outboxworker.publisher;

import com.clipforge.outboxworker.model.JobEvent;

public interface IEventPublisher {
    void publish(JobEvent event, String exchange);
}
