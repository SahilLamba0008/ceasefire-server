from exceptions.base import WorkerError


class MessagingError(WorkerError):
    """Base for errors related to the message broker (RabbitMQ)."""


class BrokerConfigError(MessagingError):
    """Raised when RabbitMQ connection configuration is invalid or missing."""
