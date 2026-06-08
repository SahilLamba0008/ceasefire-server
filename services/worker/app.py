import json
import logging
import os
import time

from bootstrap import build_pipeline
from config.settings import WORKER_MODE
from exceptions import WorkerError
from services.transcript_service import format_transcript

logging.basicConfig(
    filename="logs/app.log", level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

IS_CI = os.getenv("CI") == "true"

JOB_FILE = "job.json"
JOB_FILE_EXAMPLE = "job.example.json"


def load_video_id():
    path = JOB_FILE if os.path.exists(JOB_FILE) else JOB_FILE_EXAMPLE

    with open(path) as f:
        job = json.load(f)

    logger.info(f"Loaded video_id from {path}")
    return job["video_id"]


def run_once(video_id):
    pipeline, db = build_pipeline()
    try:
        response = pipeline.run(video_id)
        print(response)
        return response
    except WorkerError as we:
        logger.error(f"Worker error for video_id {video_id}: {str(we)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error processing video_id {video_id}: {str(e)}")
        raise
    finally:
        if db:
            db.close()
            logger.info("Database connection closed")


def idle():
    # TODO: replace with a pika consumer on the `jobs.created` queue once the
    # RabbitMQ wiring is ready — this should call run_once(video_id) per message.
    logger.info("WORKER_MODE=idle → no consumer wired up yet, idling without external calls")
    while True:
        time.sleep(3600)


def main():
    if IS_CI:
        logger.info("Running in CI mode → skipping external services")

        dummy_transcript = [{"start": 0, "text": "hello world"}]
        formatted = format_transcript(dummy_transcript)

        assert formatted is not None
        logger.info("CI boot check passed")
        return

    logger.info(f"Starting worker in WORKER_MODE={WORKER_MODE}")

    if WORKER_MODE == "once":
        run_once(load_video_id())
    else:
        idle()


if __name__ == "__main__":
    main()
