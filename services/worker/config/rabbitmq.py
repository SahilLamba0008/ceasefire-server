import logging

import pika

from config.settings import QUEUE_NAME, RABBITMQ_ENV, RABBITMQ_URL
from exceptions import BrokerConfigError

logger = logging.getLogger(__name__)

EXCHANGE_NAME = "clipforge.events"
ROUTING_KEY = "job.created"


def get_connection_params():
    if not RABBITMQ_URL:
        raise BrokerConfigError(f"RABBITMQ_URL is not configured for RABBITMQ_ENV={RABBITMQ_ENV}")

    try:
        params = pika.URLParameters(RABBITMQ_URL)
    except Exception as e:
        raise BrokerConfigError(f"Invalid RABBITMQ_URL: {e}") from e

    logger.info(
        f"RabbitMQ connection configured (env={RABBITMQ_ENV}): "
        f"host={params.host} port={params.port} vhost={params.virtual_host}"
    )

    return params


def declare_topology(channel):
    channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type="topic", durable=True)
    channel.queue_declare(queue=QUEUE_NAME, durable=True)
    channel.queue_bind(queue=QUEUE_NAME, exchange=EXCHANGE_NAME, routing_key=ROUTING_KEY)

    logger.info(
        f"Declared topology: exchange={EXCHANGE_NAME} queue={QUEUE_NAME} routing_key={ROUTING_KEY}"
    )
