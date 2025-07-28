from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable, Dict, Any
import os
import time
import uuid
from datetime import datetime
from collections import defaultdict
from src.monitoring.logger import get_logger, log_request, log_error
from src.monitoring.metrics import track_request, track_error
from src.config import settings

logger = get_logger(__name__)


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """Add correlation ID to all requests."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        correlation_id = str(uuid.uuid4())
        request.state.correlation_id = correlation_id
        
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """Log all requests and responses."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        # Get correlation ID
        correlation_id = getattr(request.state, "correlation_id", "unknown")
        
        # Log request
        logger.info(
            "request_started",
            **log_request(
                correlation_id=correlation_id,
                method=request.method,
                path=request.url.path,
                client_host=request.client.host if request.client else None,
            )
        )
        
        try:
            response = await call_next(request)
            duration = time.time() - start_time
            
            # Log response
            logger.info(
                "request_completed",
                correlation_id=correlation_id,
                status_code=response.status_code,
                duration=duration,
            )
            
            # Track metrics
            track_request(
                method=request.method,
                endpoint=request.url.path,
                status_code=response.status_code,
                duration=duration
            )
            
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "request_failed",
                **log_error(e, correlation_id=correlation_id),
                duration=duration,
            )
            track_error(error_type=type(e).__name__, endpoint=request.url.path)
            raise


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple rate limiting middleware."""
    
    def __init__(self, app):
        super().__init__(app)
        self.requests: Dict[str, list] = defaultdict(list)
        self.rate_limit = settings.rate_limit_per_minute
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting in test environment or if explicitly disabled
        if os.getenv("ENVIRONMENT") == "test" or os.getenv("DISABLE_RATE_LIMIT") == "true":
            return await call_next(request)
            
        client_ip = request.client.host if request.client else "unknown"
        now = datetime.now()
        
        # Clean old requests
        minute_ago = now.timestamp() - 60
        self.requests[client_ip] = [
            req_time for req_time in self.requests[client_ip]
            if req_time > minute_ago
        ]
        
        # Check rate limit
        if len(self.requests[client_ip]) >= self.rate_limit:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Maximum {self.rate_limit} requests per minute"
                }
            )
        
        # Record request
        self.requests[client_ip].append(now.timestamp())
        
        response = await call_next(request)
        return response


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Global error handler middleware."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)
        except HTTPException:
            raise
        except Exception as e:
            correlation_id = getattr(request.state, "correlation_id", "unknown")
            logger.error(
                "unhandled_error",
                **log_error(e, correlation_id=correlation_id),
                path=request.url.path,
            )
            
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "correlation_id": correlation_id,
                    "message": "An unexpected error occurred"
                }
            )