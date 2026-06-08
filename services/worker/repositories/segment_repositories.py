import logging
import uuid

logger = logging.getLogger(__name__)


class SegmentRepository:
    def __init__(self, conn):

        self.conn = conn

    def save_segments(self, segments):

        cursor = None

        try:
            job_id = str(uuid.UUID("d2480a02-4639-41bd-a8ee-ec8ebb82ad05"))

            query = """
                INSERT INTO segments(
                    job_id,
                    segment_start_time,
                    segment_end_time,
                    reason
                )
                VALUES(
                    %s,
                    %s,
                    %s,
                    %s
                )
            """

            cursor = self.conn.cursor()

            for segment in segments:
                cursor.execute(query, (job_id, segment["start"], segment["end"], segment["reason"]))

            self.conn.commit()

            return {"message": "segments updated successfully", "count": len(segments)}

        except Exception as e:
            self.conn.rollback()

            logger.error(f"DB insert failed {e}")

            raise

        finally:
            if cursor:
                cursor.close()
