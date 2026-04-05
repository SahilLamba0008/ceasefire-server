from fastapi import FastAPI,HTTPException
from pydantic import BaseModel
import logging 
from services.transcript_service import TranscriptService
from services.analyze_service import AnalyzeService
from utils.helpers import format_transcript, parse_segments
from config.settings import GEMINI_API_KEY

logging.basicConfig(
    filename="logs/app.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

app = FastAPI()

class VideoRequest(BaseModel):
    video_url: str
    video_id: str

@app.post("/api/generate-clips")
def generate_clips(request: VideoRequest):
    try:
        logger.info(f"Received request for video_id: {request.video_id}")
        
        # Step 1: Get transcript
        transcript_service = TranscriptService()
        transcript = transcript_service.get_transcript(request.video_id)

        # Formatting Trancript in this way [start_Time] Transcript
        formatted_transcript = format_transcript(transcript)
        analyze_service = AnalyzeService(GEMINI_API_KEY)

        #Genearting Segments Based on Transcript Data
        result = analyze_service.generate_segments(formatted_transcript)
        print("result", result)
        #Result is Coming on JSON Parsing it
        segments = parse_segments(result)
        logger.info(f"Successfully generated segments for video_id: {request.video_id}")
        return {"video_id": request.video_id, "segments": segments}
    except ValueError as ve:
        logger.error(f"Value error for video_id {request.video_id}: {str(ve)}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error processing video_id {request.video_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")