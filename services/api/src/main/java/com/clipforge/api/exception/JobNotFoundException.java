package com.clipforge.api.exception;
import org.springframework.http.HttpStatus;

public class JobNotFoundException extends ApiException {

     public JobNotFoundException(String jobId) {
        super("Job not found with id: " + jobId, HttpStatus.NOT_FOUND, "JOB_NOT_FOUND");
    }
}
