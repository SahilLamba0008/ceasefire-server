package com.clipforge.outboxworker.service;

import com.clipforge.outboxworker.config.OutboxProperties;
import com.clipforge.outboxworker.model.JobEvent;
import com.clipforge.outboxworker.publisher.IEventPublisher;
import com.clipforge.outboxworker.repository.JobEventRepository;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.stereotype.Service;

@Service
public class JobOutboxPollingService extends OutboxPollingService<JobEvent> {

    public JobOutboxPollingService(RabbitTemplate rabbit, IEventPublisher<JobEvent> publisher,
                                   JobEventRepository repository, OutboxProperties props) {
        super(rabbit, publisher, repository, props);
    }

    @Override
    protected String threadName() {
        return "job-outbox-poller";
    }
}
