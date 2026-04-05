import json
import pika

from pipeline import ingest, transcribe, analyze, render  # noqa: F401



def process_job(ch, method, properties, body):
    print("Received job", flush=True)

    try:
        job = json.loads(body)

        # Example pipeline flow
        ingest(job)
        transcribe(job)
        analyze(job)
        render(job)

        print("Job processed successfully", flush=True)

        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        print(f"Job failed: {e}", flush=True)


def main():
    print("Worker started... faaaaaaaaa", flush=True)

    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host="rabbitmq")  # match docker service name
    )
    channel = connection.channel()

    channel.queue_declare(queue="clipforge.jobs", durable=True)

    channel.basic_qos(prefetch_count=1)

    channel.basic_consume(
        queue="clipforge.jobs",
        on_message_callback=process_job
    )

    print("Not waiting for jobs... ladle x 2", flush=True)
    channel.start_consuming()



if __name__ == "__main__":
    main()