import logging 
from services.transcript_service import TranscriptService
from services.analyze_service import AnalyzeService
from services.ingest import YouTubeMetadataService
from utils.helpers import format_transcript, parse_segments
from config.settings import GEMINI_API_KEY

logging.basicConfig(
    filename="logs/app.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

try:
    video_id="5F-nvPWJqaA"
    logger.info(f"Received request for video_id: {video_id}")
        #Fetching MetadatA
    metadata_service = YouTubeMetadataService()
    metadata = metadata_service.get_metadata(video_id)
    # Step 1: Get transcript
    transcript_service = TranscriptService()
    transcript = transcript_service.get_transcript(video_id)

    # Formatting Trancript in this way [start_Time] Transcript
    formatted_transcript = format_transcript(transcript)
    analyze_service = AnalyzeService(GEMINI_API_KEY)

    #Genearting Segments Based on Transcript Data
    result = analyze_service.generate_segments(formatted_transcript)
    print("result", result)
    #Result is Coming on JSON Parsing it
    segments = parse_segments(result)
    print("metadata",metadata)
    logger.info(f"Successfully generated segments and metadata for video_id: {video_id} {segments} {metadata}")
except ValueError as ve:
    logger.error(f"Value error for video_id {video_id}: {str(ve)}")
    raise HTTPException(status_code=400, detail=str(ve))
except Exception as e:
    logger.error(f"Error processing video_id {request.video_id}: {str(e)}")
    raise HTTPException(status_code=500, detail="Internal Server Error")