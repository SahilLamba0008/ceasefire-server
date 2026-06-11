import logging

import psycopg2

from exceptions import DatabaseError
from repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class InboxRepository(BaseRepository):
    def record_event(self, message_id, event_type):
        cursor = None

        try:
            cursor = self.conn.cursor()

            cursor.execute(
                """
                INSERT INTO events.inbox_events (message_id, event_type)
                VALUES (%s, %s)
                """,
                (message_id, event_type),
            )

            self.conn.commit()
            return True

        except psycopg2.errors.UniqueViolation:
            self.conn.rollback()
            return False

        except Exception as e:
            self.conn.rollback()
            raise DatabaseError(f"Failed to record inbox event {message_id}: {e}") from e

        finally:
            if cursor:
                cursor.close()
