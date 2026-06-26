import logging

from psycopg2.extras import execute_values

from exceptions import DatabaseError

logger = logging.getLogger(__name__)


class BaseRepository:
    error_cls = DatabaseError

    def __init__(self, conn):
        self.conn = conn

    def _run_write(self, action, error_msg, error_cls=None):
        cursor = None

        try:
            cursor = self.conn.cursor()

            result = action(cursor)

            self.conn.commit()

            return result

        except Exception as e:
            self.conn.rollback()

            logger.error(f"{error_msg}: {e}")

            raise (error_cls or self.error_cls)(f"{error_msg}: {str(e)}") from e

        finally:
            if cursor:
                cursor.close()

    def _execute_write(self, query, params, error_msg, error_cls=None):
        self._run_write(lambda cursor: cursor.execute(query, params), error_msg, error_cls)

    def _execute_write_many(self, query, params_list, error_msg, error_cls=None):
        self._run_write(lambda cursor: cursor.executemany(query, params_list), error_msg, error_cls)

    def _execute_values_returning(self, query, params_list, error_msg, error_cls=None):
        return self._run_write(
            lambda cursor: execute_values(cursor, query, params_list, fetch=True),
            error_msg,
            error_cls,
        )
