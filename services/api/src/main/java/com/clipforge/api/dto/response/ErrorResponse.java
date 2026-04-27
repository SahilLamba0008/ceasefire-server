package com.clipforge.api.dto.response;

import java.time.LocalDateTime;
import java.time.ZoneOffset;

public class ErrorResponse {

    private final String message;
    private final String errorCode;
    private final LocalDateTime timestamp;

    public ErrorResponse(String message, String errorCode) {
        this.message = message;
        this.errorCode = errorCode;
        this.timestamp = LocalDateTime.now(ZoneOffset.UTC);
    }

    public String getMessage() {
        return message;
    }

    public String getErrorCode() {
        return errorCode;
    }

    public LocalDateTime getTimestamp() {
        return timestamp;
    }
}
