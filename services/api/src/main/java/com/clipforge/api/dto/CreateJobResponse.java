package com.clipforge.api.dto;

public class CreateJobResponse {
    private String jobId;
    public CreateJobResponse(String jobId) {
        this.jobId = jobId;
    }
    public String getJobId() {
        return jobId;
    }
}
