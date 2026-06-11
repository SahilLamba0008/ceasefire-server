import logging

import psycopg2

from config.settings import DATABASE_URL
from exceptions import DatabaseError

logger = logging.getLogger(__name__)


def get_connection():
    try:
        conn = psycopg2.connect(DATABASE_URL)

        dsn = conn.get_dsn_parameters()
        logger.info(
            f"Connected to database host={dsn.get('host')} port={dsn.get('port')} "
            f"dbname={dsn.get('dbname')} user={dsn.get('user')}"
        )

        return conn

    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise DatabaseError(f"Failed to connect to database: {e}") from e
