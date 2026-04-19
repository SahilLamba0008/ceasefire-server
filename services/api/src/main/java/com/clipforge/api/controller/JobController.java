package com.clipforge.api.controller;

import com.clipforge.api.dto.request.CreateJobRequest;
import com.clipforge.api.dto.response.CreateJobResponse;
import com.clipforge.api.service.JobService;

import jakarta.validation.Valid;

import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/jobs")
public class JobController {

    private final JobService jobService;

    public JobController(JobService jobService) {
        this.jobService = jobService;
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public CreateJobResponse createJob(@Valid @RequestBody CreateJobRequest request) {
        String jobId = jobService.createJob(request);
        
        CreateJobResponse response = new CreateJobResponse(jobId);
        return response;
    }
}
