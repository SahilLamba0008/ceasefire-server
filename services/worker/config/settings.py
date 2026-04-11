import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

_REQUIRED = {
    "GEMINI_API_KEY": GEMINI_API_KEY,
    "YOUTUBE_API_KEY": YOUTUBE_API_KEY,
}

_missing = [k for k, v in _REQUIRED.items() if not v]
if _missing:
    raise EnvironmentError(f"Missing Required environment variables: {', '.join(_missing)}")