import logging
import os
import tempfile

from config.database import get_connection
from repositories.clip_repository import ClipRepository
from services.extraction import _normalize_video_id, extract_segment
from storage.factory import get_storage

logger = logging.getLogger(__name__)


def _load_video_id(conn, job_id):
    cursor = None

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT youtube_url FROM jobs WHERE job_id = %s", (job_id,))
        row = cursor.fetchone()

        if not row or not row[0]:
            raise ValueError(f"No youtube_url found for job_id={job_id}")

        return _normalize_video_id(row[0])
    finally:
        if cursor:
            cursor.close()


def run(job_id, video_id=None, conn=None, storage=None, extractor=extract_segment):
    owns_connection = conn is None
    conn = conn or get_connection()
    storage = storage or get_storage()
    clip_repository = ClipRepository(conn)

    normalized_video_id = (
        _normalize_video_id(video_id) if video_id else _load_video_id(conn, job_id)
    )
    pending_clips = clip_repository.list_pending_render_clips(job_id)

    if not pending_clips:
        logger.info("No pending clips found for job_id=%s", job_id)
        return {"job_id": job_id, "rendered": 0, "failed": 0}

    rendered = 0
    failed = 0

    try:
        for clip in pending_clips:
            clip_id = clip["clip_id"]
            output_key = f"outputs/{job_id}/{clip_id}.mp4"
            temp_file = None

            try:
                clip_repository.mark_rendering(clip_id)

                temp_file = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
                temp_file.close()

                extractor(
                    normalized_video_id,
                    float(clip["segment_start_time"]),
                    float(clip["segment_end_time"]),
                    output_path=temp_file.name,
                )

                output_key = storage.save(output_key, temp_file.name)
                clip_repository.mark_rendered(clip_id, output_key)
                rendered += 1

                logger.info(
                    "Rendered clip_id=%s job_id=%s output_key=%s",
                    clip_id,
                    job_id,
                    output_key,
                )

            except Exception as error:
                failed += 1

                if output_key and storage.exists(output_key):
                    try:
                        storage.delete(output_key)
                    except Exception:
                        logger.exception(
                            "Failed to clean up stored output for clip_id=%s job_id=%s",
                            clip_id,
                            job_id,
                        )

                try:
                    clip_repository.mark_failed(clip_id, error)
                except Exception:
                    logger.exception(
                        "Failed to mark clip_id=%s as failed for job_id=%s",
                        clip_id,
                        job_id,
                    )

                logger.exception(
                    "Render failure for clip_id=%s job_id=%s",
                    clip_id,
                    job_id,
                )

            finally:
                if temp_file and os.path.exists(temp_file.name):
                    try:
                        os.unlink(temp_file.name)
                    except FileNotFoundError:
                        pass

        return {"job_id": job_id, "rendered": rendered, "failed": failed}

    finally:
        if owns_connection:
            conn.close()
