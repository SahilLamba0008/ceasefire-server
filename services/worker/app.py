import json
import logging
import os

from bootstrap import build_pipeline
from config.logging_config import setup_logging
from config.settings import WORKER_MODE
from exceptions import WorkerError
from services.event_consumer import run_consumer
from services.transcript_service import format_transcript

setup_logging()

logger = logging.getLogger(__name__)

IS_CI = os.getenv("CI") == "true"

JOB_FILE = "job.json"
JOB_FILE_EXAMPLE = "job.example.json"


def load_job_config():
    path = JOB_FILE if os.path.exists(JOB_FILE) else JOB_FILE_EXAMPLE

    with open(path) as f:
        job = json.load(f)

    logger.info(f"Loaded job config from {path}")
    return job["video_id"], job["job_id"]


def run_once(video_id, job_id):
    pipeline, conn = build_pipeline()
    try:
        response = pipeline.run(video_id, job_id)
        print(response)
        return response
    except WorkerError:
        logger.exception(f"Worker error for video_id {video_id}")
        raise
    except Exception:
        logger.exception(f"Unexpected error processing video_id {video_id}")
        raise
    finally:
        if conn:
            conn.close()
            logger.info("Database connection closed")


def idle():
    logger.info("WORKER_MODE=idle → starting RabbitMQ consumer on jobs.created")
    run_consumer()


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
        video_id, job_id = load_job_config()
        run_once(video_id, job_id)
    else:
        idle()


if __name__ == "__main__":
    main()
