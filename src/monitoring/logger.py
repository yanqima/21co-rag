import structlog
import logging
import sys
import json
import redis
import asyncio
from typing import Any, Dict, Optional
from datetime import datetime
from src.config import settings


class RedisLogProcessor:
    """Processor that saves logs to Redis for display in UI."""
    
    def __init__(self):
        self.redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            decode_responses=True
        )
        self.ttl = 3600  # 1 hour retention
        self.max_recent_logs = 1000
    
    def __call__(self, logger, method_name, event_dict):
        # Let other processors run first
        if isinstance(event_dict, str):
            return event_dict
            
        # Save to Redis asynchronously to not block
        try:
            self._save_to_redis(event_dict)
        except Exception as e:
            # Don't fail if Redis is down
            print(f"Failed to save log to Redis: {e}")
        
        return event_dict
    
    def _save_to_redis(self, event_dict):
        """Save log entry to Redis."""
        timestamp = event_dict.get('timestamp', datetime.now().isoformat())
        correlation_id = event_dict.get('correlation_id', 'none')
        
        # Create unique key
        log_key = f"log:{timestamp}:{correlation_id}:{id(event_dict)}"
        
        # Store individual log with TTL
        self.redis_client.setex(
            log_key,
            self.ttl,
            json.dumps(event_dict, default=str)
        )
        
        # Add to recent logs list
        self.redis_client.lpush("logs:recent", log_key)
        self.redis_client.ltrim("logs:recent", 0, self.max_recent_logs - 1)
        
        # Add to correlation ID index
        if correlation_id != 'none':
            corr_key = f"logs:correlation:{correlation_id}"
            self.redis_client.lpush(corr_key, log_key)
            self.redis_client.expire(corr_key, self.ttl)
            self.redis_client.ltrim(corr_key, 0, 100)  # Keep max 100 logs per correlation ID


# Global Redis processor instance
redis_log_processor = None


def setup_logging() -> None:
    """Configure structured logging for the application."""
    global redis_log_processor
    
    # Set up stdlib logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper()),
    )
    
    # Initialize Redis processor
    try:
        redis_log_processor = RedisLogProcessor()
    except Exception as e:
        print(f"Warning: Could not initialize Redis logging: {e}")
        redis_log_processor = None
    
    # Build processor list
    processors = [
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
    ]
    
    # Add Redis processor if available
    if redis_log_processor:
        processors.append(redis_log_processor)
    
    # Add final renderer
    processors.append(
        structlog.processors.JSONRenderer() if settings.environment == "production" 
        else structlog.dev.ConsoleRenderer(colors=True)
    )
    
    # Configure structlog
    structlog.configure(
        processors=processors,
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