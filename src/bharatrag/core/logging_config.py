import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict

from pythonjsonlogger.json import JsonFormatter
from bharatrag.core.context import (
    get_request_id,
    get_job_id,
    get_collection_id,
    get_document_id,
)

LOG_FORMAT = (
    "%(asctime)s | %(levelname)s | %(name)s | %(message)s | "
    "request_id=%(request_id)s job_id=%(job_id)s"
)


class ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # Try to get from context vars first, then from extra dict, then default
        record.request_id = get_request_id() or getattr(record, "request_id", None) or "-"
        record.job_id = get_job_id() or getattr(record, "job_id", None) or "-"
        record.collection_id = get_collection_id() or getattr(record, "collection_id", None) or "-"
        record.document_id = get_document_id() or getattr(record, "document_id", None) or "-"
        return True

class BharatJsonFormatter(JsonFormatter):
    """
    JSON logs that are friendly to log backends and future tracing.
    """
    
    def add_fields(
        self,
        log_data: Dict[str, Any],
        record: logging.LogRecord,
        message_dict: Dict[str, Any]
    ) -> None:
        super().add_fields(log_data, record, message_dict)
        
        # Consistent time field (RFC3339-ish)
        if "timestamp" not in log_data:
            log_data["timestamp"] = datetime.now(timezone.utc).isoformat()
        
        # Standardize level field
        log_data["level"] = record.levelname
        
        # Useful canonical fields
        log_data["logger"] = record.name
        
        # If exception info exists, include it
        if record.exc_info:
            log_data["exc_info"] = self.formatException(record.exc_info)

def setup_logging(log_level: str = "INFO") -> None:
    root = logging.getLogger()
    root.setLevel(log_level)
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    
    formatter = BharatJsonFormatter(
        fmt="%(message)s %(request_id)s %(job_id)s %(collection_id)s %(document_id)s"
    )
    handler.setFormatter(formatter)
    handler.addFilter(ContextFilter())
    
    root.handlers.clear()
    root.addHandler(handler)
