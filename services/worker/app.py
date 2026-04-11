import os
import logging
from services.transcript_service import get_transcript
from services.analyze_service import AnalyzeService
from services.ingest import YouTubeMetadataService
from utils.helpers import format_transcript, parse_segments
from config.settings import GEMINI_API_KEY
from config.settings import YOUTUBE_API_KEY

logging.basicConfig(
    filename="logs/app.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

IS_CI = os.getenv("CI") == "true"


def main():
    try:
        if IS_CI:
            logger.info("Running in CI mode → skipping external services")

            dummy_transcript = [{"start": 0, "text": "hello world"}]
            formatted = format_transcript(dummy_transcript)

            assert formatted is not None
            logger.info("CI boot check passed")
            return

        video_id = "5F-nvPWJqaA"
        logger.info(f"Received request for video_id: {video_id}")
        # Fetching MetadatA
        metadata_service = YouTubeMetadataService(YOUTUBE_API_KEY)
        metadata = metadata_service.get_metadata(video_id)
        # Step 1: Get transcript
        transcript = get_transcript(video_id)

        # Formatting Trancript in this way [start_Time] Transcript
        formatted_transcript = format_transcript(transcript)
        analyze_service = AnalyzeService(GEMINI_API_KEY)

        # Genearting Segments Based on Transcript Data
        result = analyze_service.generate_segments(formatted_transcript)
        print("result", result)
        # Result is Coming on JSON Parsing it
        segments = parse_segments(result)
        print("metadata", metadata)
        logger.info(
            f"Successfully generated segments and metadata for video_id: {video_id} {segments} {metadata}")
    except ValueError as ve:
        logger.error(f"Value error for video_id {video_id}: {str(ve)}")
        raise Exception(str(ve))
    except Exception as e:
        logger.error(f"Error processing video_id {video_id}: {str(e)}")
        raise Exception("Internal Server Error")


if __name__ == "__main__":
    main()
