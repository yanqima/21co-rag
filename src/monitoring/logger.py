import structlog
import logging
import sys
from typing import Any, Dict
from src.config import settings


def setup_logging() -> None:
    """Configure structured logging for the application."""
    
    # Set up stdlib logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper()),
    )
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.CallsiteParameterAdder(
                parameters=[
                    structlog.processors.CallsiteParameter.FILENAME,
                    structlog.processors.CallsiteParameter.FUNC_NAME,
                    structlog.processors.CallsiteParameter.LINENO,
                ]
            ),
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer() if settings.environment == "production" 
            else structlog.dev.ConsoleRenderer(colors=True),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a configured logger instance."""
    return structlog.get_logger(name)


def log_request(correlation_id: str, method: str, path: str, **kwargs: Any) -> Dict[str, Any]:
    """Create a log context for API requests."""
    return {
        "correlation_id": correlation_id,
        "method": method,
        "path": path,
        **kwargs
    }


def log_error(error: Exception, correlation_id: str = None, **kwargs: Any) -> Dict[str, Any]:
    """Create a log context for errors."""
    context = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        **kwargs
    }
    if correlation_id:
        context["correlation_id"] = correlation_id
    return context