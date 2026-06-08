import logging
import os

from config.database import get_connection
from config.settings import GEMINI_API_KEY, YOUTUBE_API_KEY
from exceptions import WorkerError
from services.analyze_service import AnalyzeService
from services.ingest import YouTubeMetadataService
from services.segment_service import SegmentService
from services.transcript_service import get_transcript
from utils.helpers import format_transcript, parse_segments

logging.basicConfig(
    filename="logs/app.log", level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

IS_CI = os.getenv("CI") == "true"


def main():
    video_id = "5F-nvPWJqaA"
    db = None
    try:
        if IS_CI:
            logger.info("Running in CI mode → skipping external services")

            dummy_transcript = [{"start": 0, "text": "hello world"}]

            formatted = format_transcript(dummy_transcript)

            assert formatted is not None
            logger.info("CI boot check passed")
            return

        logger.info(f"Received request for video_id: {video_id}")
        # Fetch YouTube metadata

        metadata_service = YouTubeMetadataService(YOUTUBE_API_KEY)

        metadata = metadata_service.get_metadata(video_id)

        logger.info(f"Metadata fetched: {metadata}")

        # Fetch transcript

        transcript = get_transcript(video_id)

        # Format transcript

        formatted_transcript = format_transcript(transcript)

        # Generate AI segments

        analyze_service = AnalyzeService(GEMINI_API_KEY)

        result = analyze_service.generate_segments(formatted_transcript)

        logger.info(f"Gemini response: {result}")

        # Parse JSON response

        segments = parse_segments(result)

        # Open DB session

        db = get_connection()

        # Save segments

        segment_service = SegmentService(db)

        response = segment_service.create_segments(segments)

        logger.info(response)
        print(response)

    except WorkerError as we:
        logger.error(f"Worker error for video_id {video_id}: {str(we)}")

        raise

    except Exception as e:
        logger.error(f"Unexpected error processing video_id {video_id}: {str(e)}")

        raise

    finally:
        if db:
            db.close()

            logger.info("Database connection closed")


if __name__ == "__main__":
    main()
