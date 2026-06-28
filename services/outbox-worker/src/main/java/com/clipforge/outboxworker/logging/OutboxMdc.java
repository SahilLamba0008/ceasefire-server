package com.clipforge.outboxworker.logging;

import com.clipforge.outboxworker.model.IOutboxEvent;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.MDC;

import java.util.Optional;
import java.util.UUID;

public final class OutboxMdc {

    private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();

    private OutboxMdc() {
    }

    public static void putEventContext(IOutboxEvent event) {
        putEventId(event.getId());
        extractJobId(event.getPayload()).ifPresent(jobId -> MDC.put("job_id", jobId));
    }

    public static void putEventContext(UUID eventId, UUID jobId) {
        putEventId(eventId);
        if (jobId != null) {
            MDC.put("job_id", jobId.toString());
        }
    }

    public static void clear() {
        MDC.clear();
    }

    private static void putEventId(UUID eventId) {
        if (eventId != null) {
            MDC.put("event_id", eventId.toString());
        }
    }

    private static Optional<String> extractJobId(String payload) {
        if (payload == null || payload.isBlank()) {
            return Optional.empty();
        }

        try {
            JsonNode root = OBJECT_MAPPER.readTree(payload);
            JsonNode jobIdNode = root.path("data").path("job_id");
            if (jobIdNode.isMissingNode() || jobIdNode.isNull()) {
                return Optional.empty();
            }

            String jobId = jobIdNode.asText();
            return jobId == null || jobId.isBlank() ? Optional.empty() : Optional.of(jobId);
        } catch (Exception ignored) {
            return Optional.empty();
        }
    }
}
