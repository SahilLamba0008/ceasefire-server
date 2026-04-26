package com.clipforge.api.service;

import com.clipforge.api.dto.request.CreateJobRequest;
import com.clipforge.api.entity.Job;
import com.clipforge.api.entity.JobEvent;
import com.clipforge.api.outbox.OutboxEventPublisher;
import com.clipforge.api.repository.JobRepository;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class JobServiceImpl implements JobService {
    private static final Logger log = LoggerFactory.getLogger(JobServiceImpl.class);
    private static final String JOB_STATUS_PENDING = JobEvent.EventStatus.PENDING.name();

    private final JobRepository jobRepository;
    private final OutboxEventPublisher outboxEventPublisher;

    public JobServiceImpl(JobRepository jobRepository, OutboxEventPublisher outboxEventPublisher) {
        this.jobRepository = jobRepository;
        this.outboxEventPublisher = outboxEventPublisher;
    }

    @Override
    @Transactional
    public String createJob(CreateJobRequest request) {
        String youtubeUrl = request.getYoutubeUrl();

        Job job = new Job();

        String title = "Job for " + youtubeUrl;
        String description = "Processing YouTube video: " + youtubeUrl;
        String status = JOB_STATUS_PENDING;

        job.setTitle(title);
        job.setDescription(description);
        job.setYoutubeUrl(youtubeUrl);
        job.setStatus(status);
        Job savedJob = jobRepository.save(job);

        outboxEventPublisher.publishJobCreated(savedJob);

        String savedJobId = savedJob.getJobId().toString();

        log.info(
            "Created job: jobId={} title=\"{}\" description=\"{}\" youtubeUrl=\"{}\" status=\"{}\"",
            savedJobId,
            savedJob.getTitle(),
            savedJob.getDescription(),
            savedJob.getYoutubeUrl(),
            savedJob.getStatus()
        );

        return savedJobId;
    }
}
