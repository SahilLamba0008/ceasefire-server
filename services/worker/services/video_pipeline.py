import logging

logger = logging.getLogger(__name__)


class VideoProcessingPipeline:
    def __init__(
        self,
        metadata_service,
        transcript_fetcher,
        transcript_formatter,
        analyze_service,
        segment_service,
    ):
        self.metadata_service = metadata_service
        self.transcript_fetcher = transcript_fetcher
        self.transcript_formatter = transcript_formatter
        self.analyze_service = analyze_service
        self.segment_service = segment_service

    def run(self, video_id, job_id):
        logger.info(f"Received request for video_id: {video_id}, job_id: {job_id}")

        metadata = self.metadata_service.get_metadata(video_id)
        logger.info(f"Metadata fetched: {metadata}")

        transcript = self.transcript_fetcher(video_id)
        formatted_transcript = self.transcript_formatter(transcript)

        result = self.analyze_service.generate_segments(formatted_transcript)
        logger.info(f"Gemini response: {result}")

        segments = self.segment_service.parse_segments(result)

        response = self.segment_service.create_segments(segments, job_id)
        logger.info(response)

        return response
