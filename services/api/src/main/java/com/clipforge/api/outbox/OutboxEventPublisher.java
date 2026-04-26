package com.clipforge.api.outbox;

import java.time.OffsetDateTime;
import java.util.UUID;

import org.springframework.stereotype.Component;

import com.clipforge.api.entity.Job;
import com.clipforge.api.entity.JobEvent;
import com.clipforge.api.entity.JobEvent.JobEventData;
import com.clipforge.api.entity.JobEvent.JobEventPayload;
import com.clipforge.api.repository.JobEventRepository;

@Component
public class OutboxEventPublisher {
    private static final int INITIAL_RETRY_COUNT = 0;
    private static final int DEFAULT_MAX_RETRIES = 5;

    private final JobEventRepository jobEventRepository;

    public OutboxEventPublisher(JobEventRepository jobEventRepository) {
        this.jobEventRepository = jobEventRepository;
    }

    public JobEvent publishJobCreated(Job job) {
        UUID outboxEventId = UUID.randomUUID();
        UUID payloadEventId = UUID.randomUUID();

        JobEventData payloadData = new JobEventData();
        payloadData.setJobId(job.getJobId());
        payloadData.setTitle(job.getTitle());
        payloadData.setDescription(job.getDescription());
        payloadData.setStatus(job.getStatus());

        JobEventPayload payload = new JobEventPayload();
        payload.setEventId(payloadEventId);
        payload.setEventType(JobEvent.EventType.JOB_CREATED.name());
        payload.setData(payloadData);

        JobEvent jobEvent = new JobEvent();
        jobEvent.setId(outboxEventId);
        jobEvent.setJobId(job.getJobId());
        jobEvent.setEventType(JobEvent.EventType.JOB_CREATED.name());
        jobEvent.setStatus(JobEvent.EventStatus.PENDING.name());
        jobEvent.setPayload(payload);
        jobEvent.setRetryCount(INITIAL_RETRY_COUNT);
        jobEvent.setMaxRetries(DEFAULT_MAX_RETRIES);
        jobEvent.setLockedBy(null);
        jobEvent.setLockedAt(null);
        jobEvent.setAvailableAt(OffsetDateTime.now());
        jobEvent.setProcessedAt(null);
        jobEvent.setLastError(null);

        return jobEventRepository.save(jobEvent);
    }
}
