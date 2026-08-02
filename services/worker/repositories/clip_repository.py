from exceptions import PersistenceError
from repositories.base import BaseRepository


class ClipRepository(BaseRepository):
    def create_pending_clips(self, segment_ids, job_id):
        query = "INSERT INTO clips (segment_id, job_id) VALUES (%s, %s)"
        params_list = [(segment_id, job_id) for segment_id in segment_ids]
        self._execute_write_many(
            query,
            params_list,
            error_msg="Failed to create pending clips",
            error_cls=PersistenceError,
        )

    def mark_rendering(self, clip_id):
        self._execute_write(
            "UPDATE clips SET status = 'rendering' WHERE clip_id = %s",
            (clip_id,),
            error_msg=f"Failed to mark clip {clip_id} as rendering",
            error_cls=PersistenceError,
        )

    def mark_rendered(self, clip_id, output_key, thumbnail_key=None):
        self._execute_write(
            """
            UPDATE clips
            SET status = 'rendered', output_key = %s, thumbnail_key = %s
            WHERE clip_id = %s
            """,
            (output_key, thumbnail_key, clip_id),
            error_msg=f"Failed to mark clip {clip_id} as rendered",
            error_cls=PersistenceError,
        )

    def mark_failed(self, clip_id, error):
        self._execute_write(
            "UPDATE clips SET status = 'failed', last_error = %s WHERE clip_id = %s",
            (str(error), clip_id),
            error_msg=f"Failed to mark clip {clip_id} as failed",
            error_cls=PersistenceError,
        )

    def list_pending_render_clips(self, job_id):
        rows = self._execute_read(
            """
            SELECT
                c.clip_id,
                c.segment_id,
                s.segment_start_time,
                s.segment_end_time
            FROM clips c
            JOIN segments s ON s.segment_id = c.segment_id
            WHERE c.job_id = %s
              AND c.status = 'pending'
            ORDER BY s.segment_start_time ASC, c.created_at ASC
            """,
            (job_id,),
            error_msg=f"Failed to load pending clips for job {job_id}",
            error_cls=PersistenceError,
        )

        return [
            {
                "clip_id": row[0],
                "segment_id": row[1],
                "segment_start_time": row[2],
                "segment_end_time": row[3],
            }
            for row in rows
        ]
