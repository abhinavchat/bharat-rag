"""
Request context management for tracking request_id, job_id, etc. across async operations.
"""
from __future__ import annotations

import contextvars
from typing import Optional
from uuid import UUID

# Context variables for request-scoped data
_request_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("request_id", default=None)
_job_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("job_id", default=None)
_collection_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("collection_id", default=None)
_document_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("document_id", default=None)


def get_request_id() -> Optional[str]:
    """Get the current request ID from context."""
    return _request_id.get()


def set_request_id(request_id: str) -> None:
    """Set the request ID in context."""
    _request_id.set(request_id)


def get_job_id() -> Optional[str]:
    """Get the current job ID from context."""
    return _job_id.get()


def set_job_id(job_id: str | UUID) -> None:
    """Set the job ID in context."""
    _job_id.set(str(job_id))


def get_collection_id() -> Optional[str]:
    """Get the current collection ID from context."""
    return _collection_id.get()


def set_collection_id(collection_id: str | UUID) -> None:
    """Set the collection ID in context."""
    _collection_id.set(str(collection_id))


def get_document_id() -> Optional[str]:
    """Get the current document ID from context."""
    return _document_id.get()


def set_document_id(document_id: str | UUID) -> None:
    """Set the document ID in context."""
    _document_id.set(str(document_id))

