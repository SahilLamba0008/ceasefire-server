from googleapiclient.discovery import build
import logging

logger = logging.getLogger(__name__)

class YouTubeMetadataService:

    def __init__(self, api_key):
        self.youtube = build('youtube', 'v3', developerKey=api_key, cache_discovery=False)

    def get_metadata(self, video_id):
        try:
            request = self.youtube.videos().list(part='snippet,statistics,contentDetails', id=video_id)
            response = request.execute()
            if not response['items']:
                raise ValueError(f"No video found with ID: {video_id}")
            data = {
                "title": response['items'][0]['snippet']['title'],
                "channelTitle": response['items'][0]['snippet']['channelTitle'],
                "publishedAt": response['items'][0]['snippet']['publishedAt'],
                "viewCount": response['items'][0]['statistics'].get('viewCount', '0'),
                "likeCount": response['items'][0]['statistics'].get('likeCount', '0'),
                "duration": response['items'][0]['contentDetails']['duration']  
            }
            return data
        except Exception as e:
            logger.error(f"Error fetching metadata for video_id {video_id}: {str(e)}")
            raise Exception(f"Failed to fetch metadata: {str(e)} for video_id: {video_id}")