from exceptions.base import WorkerError


class DatabaseError(WorkerError):
    """Base for errors originating from database operations."""


class PersistenceError(DatabaseError):
    """Raised when segments cannot be saved to the database."""
