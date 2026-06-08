from exceptions.base import WorkerError


class SegmentError(WorkerError):
    """Base for errors in the segment domain."""


class SegmentParsingError(SegmentError):
    """Raised when AI output cannot be parsed into segments."""


class SegmentValidationError(SegmentError):
    """Raised when generated segments fail validation."""
