package com.clipforge.api.service;

import com.clipforge.api.dto.request.CreateJobRequest;
import com.clipforge.api.entity.Job;
import com.clipforge.api.repository.JobRepository;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class JobServiceImpl implements JobService {
    private static final Logger log = LoggerFactory.getLogger(JobServiceImpl.class);
    private final JobRepository jobRepository;

    public JobServiceImpl(JobRepository jobRepository) {
        this.jobRepository = jobRepository;
    }

    @Override
    @Transactional
    public String createJob(CreateJobRequest request) {
        String youtubeUrl = request.getYoutubeUrl();

        Job job = new Job();

        String title = "Job for " + youtubeUrl;
        String description = "Processing YouTube video: " + youtubeUrl;
        String status = "PENDING";

        job.setTitle(title);
        job.setDescription(description);
        job.setYoutubeUrl(youtubeUrl);
        job.setStatus(status);
        Job savedJob = jobRepository.save(job);
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
