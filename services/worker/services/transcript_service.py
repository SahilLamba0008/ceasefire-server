import logging

from youtube_transcript_api import YouTubeTranscriptApi

from exceptions import TranscriptFetchError

logger = logging.getLogger(__name__)


def get_transcript(video_id):
    try:
        transcript = YouTubeTranscriptApi().fetch(
            video_id,
            languages=[
                "en",
                "en-US",
                "en-GB",
                "en-AU",
                "en-CA",
                "en-IN",
                "en-NZ",
                "en-ZA",
                "en-IE",
                "en-SG",
                "en-PH",
                "en-MY",
                "en-HK",
                "en-GB-WLS",
                "hi",
            ],
        )
        return transcript.to_raw_data()
    except Exception as e:
        logger.error(f"Error fetching transcript for video {video_id}: {e}")
        raise TranscriptFetchError(
            f"Failed to fetch transcript for video {video_id}: {str(e)}"
        ) from e


def format_transcript(transcript):
    text = ""
    for entry in transcript:
        start = entry["start"]
        content = entry["text"]
        text += f"[{start:.2f}] {content}\n"
    return text
