package com.clipforge.api.service;

import com.clipforge.api.dto.request.CreateJobRequest;
import com.clipforge.api.entity.Job;
import com.clipforge.api.repository.JobRepository;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class JobService {
    private static final Logger log = LoggerFactory.getLogger(JobService.class);
    private final JobRepository jobRepository;

    public JobService(JobRepository jobRepository) {
        this.jobRepository = jobRepository;
    }

    @Transactional // Ensure atomicity of the job creation process, handles ACID properties
    public String createJob(CreateJobRequest request) {

        String youtubeUrl = request.getYoutubeUrl();

        // Job - Entity 
        Job job = new Job();

        String title = "Job for " + request.getYoutubeUrl();
        String description = "Processing YouTube video: " + request.getYoutubeUrl();
        
        // Set job properties using - Job Entity
        job.setTitle(title);
        job.setDescription(description);
        job.setYoutubeUrl(youtubeUrl);

        // Job - Entity 
        Job savedJob = jobRepository.save(job);
        String savedJobId = savedJob.getJobId().toString(); // Id generated in Job Entity

        log.info(
            "Created job: jobId={} title=\"{}\" description=\"{}\" youtubeUrl=\"{}\"",
            savedJobId,
            savedJob.getTitle(),
            savedJob.getDescription(),
            savedJob.getYoutubeUrl()
        );

        return savedJobId;
    }
}