package com.clipforge.api.service;

import com.clipforge.api.dto.request.CreateJobRequest;

public interface JobService {
    String createJob(CreateJobRequest request);
}
