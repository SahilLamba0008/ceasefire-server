import json
import logging

import pika

from config.database import get_connection
from config.rabbitmq import declare_topology, get_connection_params
from config.settings import PREFETCH_COUNT, QUEUE_NAME
from repositories.inbox_repository import InboxRepository

logger = logging.getLogger(__name__)


def _on_message(channel, method, properties, body, inbox_repo):
    event_id = properties.message_id

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        logger.exception(f"Discarding unparseable message event_id={event_id}")
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        return

    try:
        event_type = payload.get("event_type", "")

        if inbox_repo.record_event(event_id, event_type):
            logger.info(
                f"event_id={event_id} event_type={event_type} payload={json.dumps(payload)}"
            )
            print(json.dumps(payload))
        else:
            logger.info(f"SKIP: already processed {event_id}")

        channel.basic_ack(delivery_tag=method.delivery_tag)

    except Exception:
        logger.exception(f"Failed to process message event_id={event_id}")
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


def run_consumer():
    conn = get_connection()
    inbox_repo = InboxRepository(conn)

    connection = pika.BlockingConnection(get_connection_params())
    channel = connection.channel()

    declare_topology(channel)

    channel.basic_qos(prefetch_count=PREFETCH_COUNT)
    channel.basic_consume(
        queue=QUEUE_NAME,
        on_message_callback=lambda ch, method, properties, body: _on_message(
            ch, method, properties, body, inbox_repo
        ),
    )

    logger.info(f"Consuming from queue={QUEUE_NAME} (prefetch={PREFETCH_COUNT})")

    try:
        channel.start_consuming()
    finally:
        connection.close()
        conn.close()
        logger.info("RabbitMQ connection and database connection closed")
