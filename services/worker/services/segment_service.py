import logging

from repositories.segment_repositories import SegmentRepository


logger = logging.getLogger(__name__)


class SegmentService:


    def __init__(self, db):

        self.repository = SegmentRepository(
            db
        )


    def validate_segments(
        self,
        segments
    ):

        for segment in segments:

            start_time = segment["start"]
            end_time = segment["end"]


            if start_time >= end_time:

                raise ValueError(
                    f"Invalid segment time: start {start_time} must be less than end {end_time}"
                )


        logger.info(
            "Segment validation successful"
        )



    def create_segments(
        self,
        segments
    ):

        # validation layer
        self.validate_segments(
            segments
        )


        # database layer
        self.repository.save_segments(
            segments
        )

        return {
            "message": "segments updated successfully",
            "count": len(segments)
        }