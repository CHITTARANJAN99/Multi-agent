import logging
import sys
import json
from datetime import datetime, timezone
from typing import Any
from app.config.settings import settings

class JSONFormatter(logging.Formatter):
    """
    Custom logging formatter that outputs JSON records.
    """
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "filename": record.filename,
            "line_number": record.lineno,
        }
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Append extra parameters if they exist
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)  # type: ignore

        return json.dumps(log_data)

def setup_logging() -> None:
    """
    Sets up python logging standard configurations.
    """
    root_logger = logging.getLogger()
    
    # Clear existing handlers
    root_logger.handlers = []

    # Choose formatter based on environment
    if settings.ENV == "production":
        formatter = JSONFormatter()
    else:
        # User-friendly colored format for local development
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d): %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Set logger level
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO
    root_logger.setLevel(log_level)

    # Quiet external libraries logging a bit
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    logging.info(f"Logging initialized in {settings.ENV} mode (debug={settings.DEBUG})")

logger = logging.getLogger("assistant")
