package com.clipforge.outboxworker.publisher;

import com.clipforge.outboxworker.config.OutboxProperties;
import com.clipforge.outboxworker.model.JobEvent;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.amqp.AmqpException;
import org.springframework.amqp.core.Message;
import org.springframework.amqp.core.MessageBuilder;
import org.springframework.amqp.core.MessageDeliveryMode;
import org.springframework.amqp.core.MessageProperties;
import org.springframework.amqp.rabbit.core.RabbitTemplate;

import java.nio.charset.StandardCharsets;

public abstract class RabbitMQEventPublisher implements IEventPublisher {

    private static final Logger log = LoggerFactory.getLogger(RabbitMQEventPublisher.class);

    protected final RabbitTemplate rabbit;
    protected final ObjectMapper objectMapper;
    protected final OutboxProperties props;

    protected RabbitMQEventPublisher(RabbitTemplate rabbit, ObjectMapper objectMapper, OutboxProperties props) {
        this.rabbit = rabbit;
        this.objectMapper = objectMapper;
        this.props = props;
    }

    @Override
    public final void publish(JobEvent event, String exchange) {
        JsonNode parsedPayload = parsePayload(event);
        String eventId = extractEventId(event, parsedPayload);
        String body = buildMessageBody(event, parsedPayload);
        String routingKey = eventTypeToRoutingKey(event.getEventType());

        Message message = MessageBuilder
            .withBody(body.getBytes(StandardCharsets.UTF_8))
            .setContentType(MessageProperties.CONTENT_TYPE_JSON)
            .setMessageId(eventId)
            .setDeliveryMode(MessageDeliveryMode.PERSISTENT)
            .setHeader("event_type", event.getEventType())
            .build();

        rabbit.invoke(operations -> {
            operations.send(exchange, routingKey, message);
            rabbit.waitForConfirmsOrDie(props.getPublisherConfirmTimeoutMs());
            return null;
        });

        log.debug("Broker confirmed event [id={}, type={}, routingKey={}]", eventId, event.getEventType(), routingKey);
    }

    protected abstract String buildMessageBody(JobEvent event, JsonNode parsedPayload);

    protected String extractEventId(JobEvent event, JsonNode parsedPayload) {
        JsonNode node = parsedPayload.get("event_id");
        if (node != null && !node.isNull()) return node.asText();
        return event.getId().toString();
    }

    protected String eventTypeToRoutingKey(String eventType) {
        return eventType.toLowerCase().replace('_', '.');
    }

    private JsonNode parsePayload(JobEvent event) {
        try {
            return objectMapper.readTree(event.getPayload());
        } catch (Exception e) {
            throw new AmqpException("Malformed payload JSON for event " + event.getId(), e);
        }
    }
}
