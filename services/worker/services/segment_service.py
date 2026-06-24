import json
import logging
import re

from exceptions import SegmentParsingError, SegmentValidationError
from repositories.clip_repository import ClipRepository
from repositories.segment_repositories import SegmentRepository

logger = logging.getLogger(__name__)


class SegmentService:
    def __init__(self, conn):
        self.repository = SegmentRepository(conn)
        self.clip_repository = ClipRepository(conn)

    @staticmethod
    def parse_segments(result):
        try:
            # remove markdown code block
            json_str = result.strip()

            json_str = re.sub(r"^```json", "", json_str)

            json_str = re.sub(r"^```", "", json_str)

            json_str = re.sub(r"```$", "", json_str)

            json_str = json_str.strip()

            segments = json.loads(json_str)

            return segments

        except Exception as e:
            logger.error(f"Error parsing segments: {e}")

            raise SegmentParsingError(f"Invalid JSON format: {str(e)}") from e

    def validate_segments(self, segments):

        for segment in segments:
            start_time = segment["start"]
            end_time = segment["end"]

            if start_time >= end_time:
                raise SegmentValidationError(
                    f"Invalid segment time: start {start_time} must be less than end {end_time}"
                )

        logger.info("Segment validation successful")

    def create_segments(self, segments, job_id):
        self.validate_segments(segments)

        segment_ids = self.repository.save_segments(segments, job_id)
        self.clip_repository.create_pending_clips(segment_ids, job_id)

        return {"message": "segments updated successfully", "count": len(segments)}
