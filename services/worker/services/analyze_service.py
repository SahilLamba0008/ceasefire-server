from google import genai
import logging

logger = logging.getLogger(__name__)

class AnalyzeService:

    def __init__(self, api_key):
        self.client = genai.Client(api_key=api_key)

    def generate_segments(self, transcript):
        try:
            prompt = f"""
            Return ONLY raw JSON.
            DO NOT use markdown (no ```),
            DO NOT add text before or after JSON.
            You are a viral content expert.

            The transcript may be in ANY language (Hindi, English, or mixed).
            Understand the meaning deeply regardless of language.

            Your goal:
            - Find complete, independent clips
            - Clip should start when a NEW topic or idea starts
            - Clip should end when that topic finishes
            - Clip must feel complete (no missing context)
            - Identify emotional tone even if language is Hindi
            - Prefer clips with strong expressions, storytelling, or punchlines

            Return EXACTLY 3 clips:
            [
            {{
                "start": number,
                "end": number,
                "reason": "why this is engaging"
            }}
            ]

            Rules:
            - No partial sentences
            - No context-dependent clips
            - Clip must be self-contained
            - Duration: 10 to 60 seconds (flexible)
            - Focus on:
                - emotional moments
                - storytelling
                - strong statements
                - surprising insights
            - Always align start time to beginning of a sentence
            - Always align end time to completion of a sentence or thought

            Transcript:
            {transcript}
            """

            response = self.client.models.generate_content(
                model = "gemini-2.5-flash",
                contents = prompt,)
            return response.text
        except Exception as e:
            logger.error(f"Error generating segments: {e}")
            raise Exception(f"Failed to generate segments: {str(e)}")   