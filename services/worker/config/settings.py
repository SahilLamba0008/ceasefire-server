import os

from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

# "once": process a single explicit video and exit (dev/test path)
# "idle": stay up without calling external services (default, until the
#         RabbitMQ jobs.created consumer is wired in)
WORKER_MODE = os.getenv("WORKER_MODE", "idle")
STORAGE_TYPE = os.getenv("STORAGE_TYPE", "local")
STORAGE_ROOT = os.getenv("STORAGE_ROOT", "./data/clipforge")

# "local" or "hosted" — switches which RabbitMQ URL is active without
# overwriting either value in .env
RABBITMQ_ENV = os.getenv("RABBITMQ_ENV", "local")

RABBITMQ_LOCAL_URL = os.getenv("RABBITMQ_LOCAL_URL", "amqp://guest:guest@rabbitmq:5672/%2F")
RABBITMQ_HOSTED_URL = os.getenv("RABBITMQ_HOSTED_URL")
QUEUE_NAME = os.getenv("QUEUE_NAME", "jobs.created")
PREFETCH_COUNT = int(os.getenv("PREFETCH_COUNT", "4"))

RABBITMQ_URL = RABBITMQ_HOSTED_URL if RABBITMQ_ENV == "hosted" else RABBITMQ_LOCAL_URL

_REQUIRED = {
    "GEMINI_API_KEY": GEMINI_API_KEY,
    "YOUTUBE_API_KEY": YOUTUBE_API_KEY,
    "DATABASE_URL": DATABASE_URL,
    "RABBITMQ_URL": RABBITMQ_URL,
}

_missing = [k for k, v in _REQUIRED.items() if not v]
if _missing:
    raise EnvironmentError(f"Missing Required environment variables: {', '.join(_missing)}")
