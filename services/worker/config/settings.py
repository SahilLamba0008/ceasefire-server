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

_REQUIRED = {
    "GEMINI_API_KEY": GEMINI_API_KEY,
    "YOUTUBE_API_KEY": YOUTUBE_API_KEY,
    "DATABASE_URL": DATABASE_URL,
}

_missing = [k for k, v in _REQUIRED.items() if not v]
if _missing:
    raise EnvironmentError(f"Missing Required environment variables: {', '.join(_missing)}")
