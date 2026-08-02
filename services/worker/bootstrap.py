from config.database import get_connection
from config.settings import GEMINI_API_KEY, YOUTUBE_API_KEY
from services.analyze_service import AnalyzeService
from services.ingest import YouTubeMetadataService
from services import render
from services.segment_service import SegmentService
from services.transcript_service import format_transcript, get_transcript
from services.video_pipeline import VideoProcessingPipeline


def build_pipeline():
    metadata_service = YouTubeMetadataService(YOUTUBE_API_KEY)
    analyze_service = AnalyzeService(GEMINI_API_KEY)

    conn = get_connection()
    segment_service = SegmentService(conn)

    pipeline = VideoProcessingPipeline(
        metadata_service=metadata_service,
        transcript_fetcher=get_transcript,
        transcript_formatter=format_transcript,
        analyze_service=analyze_service,
        segment_service=segment_service,
        render_runner=render.run,
    )

    return pipeline, conn
