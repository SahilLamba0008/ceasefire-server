from exceptions.base import WorkerError


class ExternalServiceError(WorkerError):
    """Base for errors originating from third-party API calls."""


class MetadataFetchError(ExternalServiceError):
    """Raised when YouTube metadata cannot be retrieved."""


class TranscriptFetchError(ExternalServiceError):
    """Raised when a transcript cannot be retrieved."""


class SegmentGenerationError(ExternalServiceError):
    """Raised when the AI fails to produce segments."""
