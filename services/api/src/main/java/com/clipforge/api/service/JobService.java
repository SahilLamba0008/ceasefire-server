package com.clipforge.api.service;
import java.util.UUID;

import org.springframework.stereotype.Service;

import com.clipforge.api.dto.CreateJobRequest;
import com.clipforge.api.entity.Job;
import com.clipforge.api.repository.JobRepository;

@Service
public class JobService {
    private final JobRepository jobRepository;

    public JobService(JobRepository jobRepository) {
        this.jobRepository = jobRepository;
    }

    public String createJob(CreateJobRequest request) {
        // 1. Generate unique job_id
        String jobId = UUID.randomUUID().toString();
        String title = request.getTitle();
        String description = request.getDescription();
        String youtubeUrl = request.getYoutubeUrl();
        
        // 2. Prepare data (logs to check)
        System.out.println("Creating job:");
        System.out.println("ID: " + jobId);
        System.out.println("Title: " + title);
        System.out.println("Description: " + description);
        System.out.println("YouTube URL: " + youtubeUrl);

        Job job = new Job();
        job.setJobId(jobId);
        job.setTitle(title);
        job.setDescription(description);
        job.setYoutubeUrl(youtubeUrl);


        // 🔥 THIS WAS MISSING`
        jobRepository.save(job);

        return jobId;
    }
}