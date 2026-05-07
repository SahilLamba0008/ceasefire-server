package com.clipforge.api.exception;

public class JobCreationException extends ApiException {

    public JobCreationException(String message) {
        super(message);
    }

    public JobCreationException(String message, Throwable cause) {
        super(message, cause);
    }
}
