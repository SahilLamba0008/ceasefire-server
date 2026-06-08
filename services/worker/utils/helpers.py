import json
import logging
import re

logger = logging.getLogger(__name__)


# Convert transcript to readable text
def format_transcript(transcript):
    text = ""
    for entry in transcript:
        start = entry["start"]
        content = entry["text"]
        text += f"[{start:.2f}] {content}\n"
    return text


def parse_segments(result):
    try:
        # remove markdown code block
        json_str = result.strip()

        json_str = re.sub(r"^```json", "", json_str)

        json_str = re.sub(r"^```", "", json_str)

        json_str = re.sub(r"```$", "", json_str)

        json_str = json_str.strip()

        segments = json.loads(json_str)

        return segments

    except Exception as e:
        logger.error(f"Error parsing segments: {e}")

        raise ValueError(f"Invalid JSON format: {str(e)}")
