package com.clipforge.api.exception;
import org.springframework.http.HttpStatus;

public class JobCreationException extends ApiException {

    public JobCreationException(String message) {
        super(message, HttpStatus.INTERNAL_SERVER_ERROR, "JOB_CREATION_FAILED");
    }

    public JobCreationException(String message, Throwable cause) {
        super(message, cause, HttpStatus.INTERNAL_SERVER_ERROR, "JOB_CREATION_FAILED");
    }
}
