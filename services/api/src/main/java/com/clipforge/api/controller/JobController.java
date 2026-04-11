package com.clipforge.api.controller;

import com.clipforge.api.dto.CreateJobRequest;
import com.clipforge.api.service.JobService;

import jakarta.validation.Valid;

import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/jobs")
public class JobController {

    private final JobService jobService;

    public JobController(JobService jobService) {
        this.jobService = jobService;
    }

    @PostMapping
    public String createJob(@Valid @RequestBody CreateJobRequest request) {
        return jobService.createJob(request);
    }
}