import psycopg2
from config.settings import DATABASE_URL


def get_connection():

    conn = psycopg2.connect(
        DATABASE_URL
    )

    return conn