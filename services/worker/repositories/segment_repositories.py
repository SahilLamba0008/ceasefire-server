from exceptions import PersistenceError
from repositories.base import BaseRepository


class SegmentRepository(BaseRepository):
    def save_segments(self, segments, job_id):
        query = """
            INSERT INTO segments (job_id, segment_start_time, segment_end_time, reason)
            VALUES (%s, %s, %s, %s)
        """

        params_list = [
            (job_id, segment["start"], segment["end"], segment["reason"]) for segment in segments
        ]

        self._execute_write_many(
            query,
            params_list,
            error_msg="Failed to save segments",
            error_cls=PersistenceError,
        )

        return {"message": "segments updated successfully", "count": len(segments)}
