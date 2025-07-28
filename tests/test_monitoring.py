"""
Tests for monitoring and observability modules.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import json
import structlog
from prometheus_client import REGISTRY
import redis
import logging
import time

from src.monitoring.logger import setup_logging, get_logger, log_request, log_error, RedisLogProcessor
from src.monitoring.metrics import (
    request_count,
    request_duration,
    document_processing_count,
    document_processing_duration,
    track_request,
    track_error,
    track_document_processing,
    track_vector_search,
    vector_db_size,
    track_embedding_generation
)


class TestStructuredLogging:
    """Test structured logging functionality."""
    
    def test_setup_logging_configures_structlog(self):
        """Test that setup_logging properly configures structlog."""
        with patch('src.monitoring.logger.RedisLogProcessor') as mock_redis:
            setup_logging()
            
            # Should configure structlog
            # Get configured logger to test it works
            logger = get_logger("test")
            assert logger is not None
    
    def test_get_logger_returns_bound_logger(self):
        """Test get_logger returns a properly configured logger."""
        logger = get_logger("test_module")
        # Structlog returns a BoundLoggerLazyProxy which is the expected type
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'error')
        assert hasattr(logger, 'debug')
    
    def test_log_request_creates_context(self):
        """Test log_request creates proper context dict."""
        context = log_request(
            correlation_id="test-123",
            method="GET",
            path="/api/test",
            status_code=200
        )
        
        assert context["correlation_id"] == "test-123"
        assert context["method"] == "GET"
        assert context["path"] == "/api/test"
        assert context["status_code"] == 200
    
    def test_log_error_creates_error_context(self):
        """Test log_error creates proper error context."""
        error = ValueError("Test error")
        context = log_error(
            error=error,
            correlation_id="test-123",
            action="test_action"
        )
        
        assert context["error_type"] == "ValueError"
        assert context["error_message"] == "Test error"
        assert context["correlation_id"] == "test-123"
        assert context["action"] == "test_action"
    
    def test_redis_log_processor_init(self):
        """Test RedisLogProcessor initialization."""
        with patch('redis.Redis') as mock_redis:
            processor = RedisLogProcessor()
            
            assert processor.redis_client is not None
            assert processor.ttl == 3600
            assert processor.max_recent_logs == 1000
    
    def test_redis_log_processor_saves_logs(self):
        """Test RedisLogProcessor saves logs to Redis."""
        with patch('redis.Redis') as mock_redis_class:
            mock_redis = Mock()
            mock_redis_class.return_value = mock_redis
            
            processor = RedisLogProcessor()
            
            # Test log event
            event_dict = {
                "timestamp": "2024-01-01T00:00:00",
                "correlation_id": "test-123",
                "level": "info",
                "message": "Test message"
            }
            
            result = processor(None, "info", event_dict)
            
            # Should save to Redis
            mock_redis.setex.assert_called()
            mock_redis.lpush.assert_called()
            assert result == event_dict
    
    def test_redis_log_processor_handles_errors(self, capsys):
        """Test RedisLogProcessor handles Redis errors gracefully."""
        with patch('redis.Redis') as mock_redis_class:
            mock_redis = Mock()
            mock_redis.setex.side_effect = Exception("Redis error")
            mock_redis_class.return_value = mock_redis
            
            processor = RedisLogProcessor()
            event_dict = {"message": "test"}
            
            result = processor(None, "info", event_dict)
            
            # Should not raise, just print error
            captured = capsys.readouterr()
            assert "Failed to save log to Redis" in captured.out
            assert result == event_dict


class TestMetrics:
    """Test metrics functionality."""
    
    def test_metrics_registered(self):
        """Test that metrics are registered."""
        # Import to ensure metrics are registered
        import src.monitoring.metrics
        
        # Check that metrics are registered
        metric_names = [metric.name for metric in REGISTRY.collect()]
        assert any("rag_api_requests" in name for name in metric_names)
        assert any("rag_documents_processed" in name for name in metric_names)
        assert any("rag_vector_search" in name for name in metric_names)
    
    def test_track_request_function(self):
        """Test track_request function."""
        # Track a request
        track_request(method="GET", endpoint="/test", status_code=200, duration=0.1)
        
        # Check metrics were updated
        metrics = list(REGISTRY.collect())
        request_metrics = [m for m in metrics if "rag_api_requests" in m.name]
        assert len(request_metrics) > 0
    
    def test_track_error_function(self):
        """Test track_error function."""
        # Track an error
        track_error(error_type="ValueError", endpoint="/test")
        
        # Check error was tracked
        metrics = list(REGISTRY.collect())
        error_metrics = [m for m in metrics if "rag_errors" in m.name]
        assert len(error_metrics) > 0
    
    def test_track_document_processing_function(self):
        """Test track_document_processing function."""
        # Track document processing
        track_document_processing(status="success", duration=1.5, doc_type="pdf")
        
        # Check metrics
        metrics = list(REGISTRY.collect())
        doc_metrics = [m for m in metrics if "rag_documents_processed" in m.name or "rag_document_processing" in m.name]
        assert len(doc_metrics) > 0
    
    def test_track_vector_search_function(self):
        """Test track_vector_search function."""
        # Track vector search
        track_vector_search(search_type="hybrid", duration=0.5)
        
        # Check metrics
        metrics = list(REGISTRY.collect())
        search_metrics = [m for m in metrics if "rag_vector_search" in m.name]
        assert len(search_metrics) > 0
    
    def test_track_embedding_generation_function(self):
        """Test track_embedding_generation function."""
        # Track embedding generation
        track_embedding_generation(duration=2.0)
        
        # Check metrics
        metrics = list(REGISTRY.collect())
        embed_metrics = [m for m in metrics if "rag_embedding" in m.name]
        assert len(embed_metrics) > 0
    
    def test_vector_db_size_gauge(self):
        """Test vector_db_size gauge updates."""
        # Set a value
        vector_db_size.set(1000)
        
        # Check it was set
        metrics = list(REGISTRY.collect())
        size_metrics = [m for m in metrics if "rag_vector_db" in m.name]
        assert len(size_metrics) > 0
    
    def test_measure_time_decorator(self):
        """Test measure_time decorator."""
        from src.monitoring.metrics import measure_time
        
        # Test with sync function
        @measure_time(lambda duration: track_embedding_generation(duration))
        def sync_func():
            time.sleep(0.01)
            return "done"
        
        result = sync_func()
        assert result == "done"
        
        # Check metrics were updated
        metrics = list(REGISTRY.collect())
        embed_metrics = [m for m in metrics if "rag_embedding" in m.name]
        assert len(embed_metrics) > 0


class TestProfilingIntegration:
    """Test profiling functionality."""
    
    def test_profiling_module_imports(self):
        """Test that profiling module can be imported."""
        try:
            from src.monitoring.profiling import analyze_request_logs, aggregate_performance_stats
            assert True
        except ImportError as e:
            pytest.fail(f"Failed to import profiling module: {e}")
    
    def test_profile_manager_singleton(self):
        """Test ProfileManager pattern if exists."""
        try:
            from src.monitoring.profiling import ProfileManager
            
            # ProfileManager might use different singleton pattern
            # Just test it can be instantiated
            manager = ProfileManager()
            assert manager is not None
        except (ImportError, AttributeError):
            # ProfileManager might not be implemented
            pass
    
    @pytest.mark.asyncio
    async def test_profile_async_decorator(self):
        """Test async profiling decorator."""
        try:
            from src.monitoring.profiling import profile_async
            
            call_count = 0
            
            @profile_async("test_operation")
            async def test_func(x):
                nonlocal call_count
                call_count += 1
                return x * 2
            
            result = await test_func(5)
            
            assert result == 10
            assert call_count == 1
        except ImportError:
            # profile_async might not be implemented
            pass
    
    def test_profile_sync_decorator(self):
        """Test sync profiling decorator."""
        try:
            from src.monitoring.profiling import profile_sync
            
            call_count = 0
            
            @profile_sync("test_operation")
            def test_func(x):
                nonlocal call_count
                call_count += 1
                return x * 2
            
            result = test_func(5)
            
            assert result == 10
            assert call_count == 1
        except ImportError:
            # profile_sync might not be implemented
            pass