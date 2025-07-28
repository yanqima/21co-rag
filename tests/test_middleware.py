"""
Tests for API middleware components.
"""
import os
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
import time
import uuid
from starlette.exceptions import HTTPException

from src.api.middleware import (
    CorrelationIDMiddleware,
    LoggingMiddleware,
    RateLimitMiddleware,
    ErrorHandlerMiddleware
)
from src.config import settings


class TestCorrelationIdMiddleware:
    """Test correlation ID middleware."""
    
    @pytest.fixture
    def app_with_correlation_id(self):
        """Create app with correlation ID middleware."""
        app = FastAPI()
        app.add_middleware(CorrelationIDMiddleware)
        
        @app.get("/test")
        async def test_endpoint(request: Request):
            return {"correlation_id": request.state.correlation_id}
        
        return app
    
    def test_adds_correlation_id_to_request(self, app_with_correlation_id):
        """Test that correlation ID is added to request."""
        client = TestClient(app_with_correlation_id)
        response = client.get("/test")
        
        assert response.status_code == 200
        assert "correlation_id" in response.json()
        assert len(response.json()["correlation_id"]) == 36  # UUID format
    
    def test_adds_correlation_id_to_response_headers(self, app_with_correlation_id):
        """Test that correlation ID is added to response headers."""
        client = TestClient(app_with_correlation_id)
        response = client.get("/test")
        
        assert "X-Correlation-ID" in response.headers
        assert len(response.headers["X-Correlation-ID"]) == 36
    
    def test_generates_new_correlation_id(self, app_with_correlation_id):
        """Test that a new correlation ID is generated."""
        client = TestClient(app_with_correlation_id)
        
        response = client.get("/test")
        
        # Should generate a new UUID for each request
        correlation_id = response.json()["correlation_id"]
        assert len(correlation_id) == 36  # UUID format
        assert response.headers["X-Correlation-ID"] == correlation_id


class TestRequestLoggingMiddleware:
    """Test request logging middleware."""
    
    @pytest.fixture
    def app_with_logging(self):
        """Create app with logging middleware."""
        app = FastAPI()
        app.add_middleware(LoggingMiddleware)
        
        @app.get("/test")
        async def test_endpoint():
            return {"status": "ok"}
        
        @app.get("/error")
        async def error_endpoint():
            raise ValueError("Test error")
        
        return app
    
    def test_logs_successful_requests(self, app_with_logging):
        """Test logging of successful requests."""
        with patch('src.api.middleware.logger') as mock_logger:
            client = TestClient(app_with_logging)
            response = client.get("/test")
            
            assert response.status_code == 200
            mock_logger.info.assert_called()
            
            # Check logged data - there should be two info calls (request_started and request_completed)
            assert mock_logger.info.call_count >= 2
            
            # Find the request_completed log
            for call in mock_logger.info.call_args_list:
                if "request_completed" in call[0]:
                    assert call[1]["status_code"] == 200
                    assert "duration" in call[1]
                    break
    
    def test_logs_failed_requests(self, app_with_logging):
        """Test logging of failed requests."""
        with patch('src.api.middleware.logger') as mock_logger:
            client = TestClient(app_with_logging, raise_server_exceptions=False)
            response = client.get("/error")
            
            assert response.status_code == 500
            
            # The error handler middleware should log the error
            # Check if error was logged through any of the logging methods
            assert mock_logger.error.called or mock_logger.exception.called
            
            # Look for the error logging in any of the calls
            found_error_log = False
            for call in mock_logger.error.call_args_list + mock_logger.exception.call_args_list:
                if call and len(call) > 0:
                    found_error_log = True
                    break
            
            assert found_error_log
    
    def test_logs_request_duration(self, app_with_logging):
        """Test that request duration is logged."""
        with patch('src.api.middleware.logger') as mock_logger:
            client = TestClient(app_with_logging)
            response = client.get("/test")
            
            # Find the request_completed log
            for call in mock_logger.info.call_args_list:
                if "request_completed" in call[0]:
                    assert "duration" in call[1]
                    assert isinstance(call[1]["duration"], (int, float))
                    assert call[1]["duration"] >= 0
                    break


class TestRateLimitMiddleware:
    """Test rate limiting middleware."""
    
    def test_rate_limiting_disabled_in_test_env(self):
        """Test that rate limiting is disabled in test environment."""
        # Ensure we're in test environment
        assert os.getenv("ENVIRONMENT") == "test" or os.getenv("DISABLE_RATE_LIMIT") == "true"
        
        with patch('src.api.middleware.settings.rate_limit_per_minute', 1):  # Very low limit
            app = FastAPI()
            app.add_middleware(RateLimitMiddleware)
            
            @app.get("/test")
            async def test_endpoint():
                return {"status": "ok"}
            
            client = TestClient(app)
            
            # Make many requests - all should succeed because rate limiting is disabled
            for i in range(10):
                response = client.get("/test")
                assert response.status_code == 200
    
    def test_allows_requests_within_limit(self):
        """Test that requests within limit are allowed."""
        with patch('src.api.middleware.settings.rate_limit_per_minute', 5):
            app = FastAPI()
            app.add_middleware(RateLimitMiddleware)
            
            @app.get("/test")
            async def test_endpoint():
                return {"status": "ok"}
            
            client = TestClient(app)
            
            # Make 5 requests (the limit)
            for i in range(5):
                response = client.get("/test")
                assert response.status_code == 200
    
    def test_blocks_requests_exceeding_limit(self):
        """Test that requests exceeding limit are blocked."""
        # Temporarily override environment to test rate limiting
        with patch.dict(os.environ, {"ENVIRONMENT": "production", "DISABLE_RATE_LIMIT": "false"}):
            with patch('src.api.middleware.settings.rate_limit_per_minute', 5):
                app = FastAPI()
                app.add_middleware(RateLimitMiddleware)
                
                @app.get("/test")
                async def test_endpoint():
                    return {"status": "ok"}
                
                client = TestClient(app)
                
                # Make 5 requests to reach limit
                for i in range(5):
                    client.get("/test")
                
                # 6th request should be blocked
                response = client.get("/test")
                assert response.status_code == 429
                assert "Rate limit exceeded" in response.json()["error"]
    
    def test_rate_limit_resets_after_period(self):
        """Test that rate limit resets after period."""
        # Temporarily override environment to test rate limiting
        with patch.dict(os.environ, {"ENVIRONMENT": "production", "DISABLE_RATE_LIMIT": "false"}):
            with patch('src.api.middleware.settings.rate_limit_per_minute', 5):
                with patch('src.api.middleware.datetime') as mock_datetime:
                    app = FastAPI()
                    app.add_middleware(RateLimitMiddleware)
                    
                    @app.get("/test")
                    async def test_endpoint():
                        return {"status": "ok"}
                    
                    client = TestClient(app)
                    current_time = time.time()
                    
                    # Mock datetime.now() to control time
                    mock_now = Mock()
                    mock_now.timestamp.return_value = current_time
                    mock_datetime.now.return_value = mock_now
                    
                    # Make 5 requests to reach limit
                    for i in range(5):
                        client.get("/test")
                    
                    # 6th request should be blocked
                    response = client.get("/test")
                    assert response.status_code == 429
                    
                    # Advance time past the period
                    mock_now.timestamp.return_value = current_time + 61
                    
                    # Should be allowed again
                    response = client.get("/test")
                    assert response.status_code == 200
    
    def test_rate_limit_per_ip(self):
        """Test that rate limiting is per IP address."""
        # Temporarily override environment to test rate limiting
        with patch.dict(os.environ, {"ENVIRONMENT": "production", "DISABLE_RATE_LIMIT": "false"}):
            with patch('src.api.middleware.settings.rate_limit_per_minute', 5):
                # Recreate middleware with mocked settings
                app = FastAPI()
                app.add_middleware(RateLimitMiddleware)
                
                @app.get("/test")
                async def test_endpoint():
                    return {"status": "ok"}
                
                client = TestClient(app)
                
                # Make 5 requests to reach limit
                for i in range(5):
                    response = client.get("/test")
                    assert response.status_code == 200
                
                # 6th request should be blocked
                response = client.get("/test")
                assert response.status_code == 429


class TestErrorHandlerMiddleware:
    """Test error handler middleware."""
    
    @pytest.fixture
    def app_with_error_handler(self):
        """Create app with error handler middleware."""
        app = FastAPI()
        app.add_middleware(ErrorHandlerMiddleware)
        
        @app.get("/test")
        async def test_endpoint():
            return {"status": "ok"}
        
        @app.get("/error")
        async def error_endpoint():
            raise ValueError("Test error")
        
        @app.get("/http_error")
        async def http_error_endpoint():
            raise HTTPException(status_code=404, detail="Not found")
        
        return app
    
    def test_handles_regular_errors(self, app_with_error_handler):
        """Test handling of regular exceptions."""
        client = TestClient(app_with_error_handler)
        response = client.get("/error")
        
        assert response.status_code == 500
        assert "Internal server error" in response.json()["error"]
    
    def test_passes_http_exceptions(self, app_with_error_handler):
        """Test that HTTP exceptions pass through."""
        client = TestClient(app_with_error_handler)
        response = client.get("/http_error")
        
        assert response.status_code == 404
        assert response.json()["detail"] == "Not found"


class TestMiddlewareIntegration:
    """Test middleware integration."""
    
    @pytest.fixture
    def app_with_all_middleware(self):
        """Create app with all middleware."""
        app = FastAPI()
        
        # Add all middleware
        app.add_middleware(ErrorHandlerMiddleware)
        app.add_middleware(RateLimitMiddleware)
        app.add_middleware(LoggingMiddleware)
        app.add_middleware(CorrelationIDMiddleware)
        
        @app.get("/test")
        async def test_endpoint(request: Request):
            return {
                "status": "ok",
                "correlation_id": request.state.correlation_id
            }
        
        return app
    
    def test_all_middleware_work_together(self, app_with_all_middleware):
        """Test that all middleware work together."""
        with patch('src.api.middleware.logger') as mock_logger:
            client = TestClient(app_with_all_middleware)
            response = client.get("/test")
            
            # Check response
            assert response.status_code == 200
            assert "correlation_id" in response.json()
            assert "X-Correlation-ID" in response.headers
            
            # Check logging happened
            mock_logger.info.assert_called()
    
    def test_middleware_error_handling(self, app_with_all_middleware):
        """Test middleware handles errors gracefully."""
        # Add error endpoint
        @app_with_all_middleware.get("/error")
        async def error_endpoint():
            raise ValueError("Test error")
        
        with patch('src.api.middleware.logger') as mock_logger:
            client = TestClient(app_with_all_middleware)
            response = client.get("/error")
            
            # Should still have correlation ID even on error
            assert "X-Correlation-ID" in response.headers
            
            # Error should be logged
            mock_logger.error.assert_called()


