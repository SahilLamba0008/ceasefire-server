package com.clipforge.outboxworker.publisher;

import com.clipforge.outboxworker.config.OutboxProperties;
import com.clipforge.outboxworker.model.JobEvent;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.springframework.amqp.AmqpException;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.stereotype.Component;

import java.time.Instant;

@Component
public class JobEventPublisher extends RabbitMQEventPublisher<JobEvent> {

    public JobEventPublisher(RabbitTemplate rabbit, ObjectMapper objectMapper, OutboxProperties props) {
        super(rabbit, objectMapper, props);
    }

    @Override
    protected String buildMessageBody(JobEvent event, JsonNode parsedPayload) {
        try {
            ObjectNode out = objectMapper.createObjectNode();
            out.put("event_id", parsedPayload.path("event_id").asText(event.getId().toString()));
            out.put("event_type", event.getEventType());
            out.put("occurred_at", occurredAt(event));
            out.set("payload", parsedPayload.path("data"));
            return objectMapper.writeValueAsString(out);
        } catch (Exception e) {
            throw new AmqpException("Failed to build message body for event " + event.getId(), e);
        }
    }

    private String occurredAt(JobEvent event) {
        if (event.getCreatedAt() != null) return event.getCreatedAt().toInstant().toString();
        return Instant.now().toString();
    }
}
