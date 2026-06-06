package com.clipforge.outboxworker.config;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.amqp.core.Binding;
import org.springframework.amqp.core.BindingBuilder;
import org.springframework.amqp.core.Queue;
import org.springframework.amqp.core.QueueBuilder;
import org.springframework.amqp.core.TopicExchange;
import org.springframework.amqp.rabbit.connection.ConnectionFactory;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class RabbitMQConfig {

    @Bean
    public TopicExchange clipforgeEventsExchange(OutboxProperties props) {
        return new TopicExchange(props.getExchange(), true, false);
    }

    @Bean
    public Queue jobCreatedQueue() {
        return QueueBuilder.durable("jobs.created").build();
    }

    @Bean
    public Binding jobCreatedBinding(Queue jobCreatedQueue, TopicExchange clipforgeEventsExchange) {
        return BindingBuilder.bind(jobCreatedQueue).to(clipforgeEventsExchange).with("job.created");
    }

    @Bean
    public RabbitTemplate rabbitTemplate(ConnectionFactory connectionFactory) {
        RabbitTemplate template = new RabbitTemplate(connectionFactory);
        template.setMandatory(true);
        return template;
    }

    @Bean
    public ObjectMapper objectMapper() {
        return new ObjectMapper();
    }
}
