from exceptions import PersistenceError
from repositories.base import BaseRepository


class SegmentRepository(BaseRepository):
    def save_segments(self, segments, job_id):
        query = """
            INSERT INTO segments (job_id, segment_start_time, segment_end_time, reason)
            VALUES %s
            RETURNING segment_id
        """

        params_list = [
            (job_id, segment["start"], segment["end"], segment["reason"]) for segment in segments
        ]

        rows = self._execute_values_returning(
            query,
            params_list,
            error_msg="Failed to save segments",
            error_cls=PersistenceError,
        )

        return [row[0] for row in rows]
