import logging
import shlex
import subprocess
import threading
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from exceptions import ExternalServiceError

logger = logging.getLogger(__name__)

_URL_CACHE = {}
_URL_CACHE_LOCK = threading.Lock()
_URL_CACHE_TTL_SECONDS = 5 * 60 * 60
_PRE_ROLL_SECONDS = 2


def _normalize_video_id(value):
    if not value:
        raise ValueError("video_id is required")

    parsed = urlparse(value)
    if not parsed.scheme and not parsed.netloc:
        return value

    query_values = parse_qs(parsed.query).get("v")
    if query_values:
        return query_values[0]

    path_parts = [part for part in parsed.path.split("/") if part]
    if parsed.netloc.endswith("youtu.be") and path_parts:
        return path_parts[0]

    if path_parts:
        return path_parts[-1]

    return value


def resolve_cdn_urls(video_id, quality):
    normalized_video_id = _normalize_video_id(video_id)
    cache_key = f"{normalized_video_id}:{quality}"
    now = time.monotonic()

    with _URL_CACHE_LOCK:
        cached = _URL_CACHE.get(cache_key)
        if cached and cached[0] > now:
            return cached[1]

    youtube_url = f"https://www.youtube.com/watch?v={normalized_video_id}"
    format_selector = f"bv*[height<={quality}]+ba/b[height<={quality}]"
    command = [
        "yt-dlp",
        "--no-playlist",
        "--quiet",
        "--no-warnings",
        "-f",
        format_selector,
        "-g",
        youtube_url,
    ]

    logger.info("Resolving CDN URLs with command: %s", shlex.join(command))
    result = subprocess.run(command, capture_output=True, text=True, check=False)

    if result.returncode != 0:
        raise ExternalServiceError(
            f"yt-dlp failed for video_id={normalized_video_id}: {result.stderr.strip()}"
        )

    urls = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if not urls:
        raise ExternalServiceError(
            f"yt-dlp returned no CDN URLs for video_id={normalized_video_id}"
        )

    video_url = urls[0]
    audio_url = urls[1] if len(urls) > 1 else urls[0]
    resolved = (video_url, audio_url)

    with _URL_CACHE_LOCK:
        _URL_CACHE[cache_key] = (now + _URL_CACHE_TTL_SECONDS, resolved)

    logger.info(
        "Resolved CDN URLs for video_id=%s quality=%s video_url=%s audio_url=%s",
        normalized_video_id,
        quality,
        video_url,
        audio_url,
    )
    return resolved


def extract_segment(video_id, start, end, quality="720", output_path=None):
    if end <= start:
        raise ValueError("end must be greater than start")

    if output_path is None:
        raise ValueError("output_path is required")

    normalized_video_id = _normalize_video_id(video_id)
    video_url, audio_url = resolve_cdn_urls(normalized_video_id, quality)

    preroll_start = max(float(start) - _PRE_ROLL_SECONDS, 0)
    output_trim = float(start) - preroll_start
    duration = float(end) - float(start)
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "info",
        "-ss",
        str(preroll_start),
        "-i",
        video_url,
        "-ss",
        str(preroll_start),
        "-i",
        audio_url,
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-ss",
        str(output_trim),
        "-t",
        str(duration),
        "-c:v",
        "libx264",
        "-c:a",
        "aac",
        "-movflags",
        "+faststart",
        str(Path(output_path)),
    ]

    logger.info(
        "Extracting segment video_id=%s start=%s end=%s quality=%s output=%s command=%s",
        normalized_video_id,
        start,
        end,
        quality,
        output_path,
        shlex.join(command),
    )

    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise ExternalServiceError(
            "ffmpeg failed for video_id="
            f"{normalized_video_id} start={start} end={end}: {result.stderr.strip()}"
        )

    return str(Path(output_path))
