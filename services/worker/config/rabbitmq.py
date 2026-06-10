import logging

import pika

from config.settings import RABBITMQ_ENV, RABBITMQ_URL
from exceptions import BrokerConfigError

logger = logging.getLogger(__name__)


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
