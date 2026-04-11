import json

# Convert transcript to readable text
def format_transcript(transcript):
    text = ""
    for entry in transcript:
        start = entry['start']
        content = entry['text']
        text += f"[{start:.2f}] {content}\n"
    return text

def parse_segments(json_str):
    try:
        segments = json.loads(json_str)
        return segments
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format: {str(e)}")