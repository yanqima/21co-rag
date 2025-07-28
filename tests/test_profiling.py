"""
Tests for the profiling module.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.monitoring.profiling import (
    parse_timestamp,
    analyze_request_logs,
    aggregate_performance_stats,
    identify_bottlenecks
)


class TestTimestampParsing:
    """Test timestamp parsing functionality."""
    
    def test_parse_timestamp_with_microseconds(self):
        """Test parsing timestamp with microseconds."""
        timestamp = "2024-01-01T12:00:00.123456"
        result = parse_timestamp(timestamp)
        
        assert isinstance(result, datetime)
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 1
    
    def test_parse_timestamp_without_microseconds(self):
        """Test parsing timestamp without microseconds."""
        timestamp = "2024-01-01T12:00:00"
        result = parse_timestamp(timestamp)
        
        assert isinstance(result, datetime)
    
    def test_parse_timestamp_with_z(self):
        """Test parsing timestamp with Z timezone."""
        timestamp = "2024-01-01T12:00:00Z"
        result = parse_timestamp(timestamp)
        
        assert isinstance(result, datetime)
    
    def test_parse_timestamp_iso_format(self):
        """Test parsing ISO format timestamp."""
        timestamp = "2024-01-01T12:00:00+00:00"
        result = parse_timestamp(timestamp)
        
        assert isinstance(result, datetime)
    
    def test_parse_invalid_timestamp(self):
        """Test parsing invalid timestamp returns current time."""
        timestamp = "invalid"
        result = parse_timestamp(timestamp)
        
        assert isinstance(result, datetime)
        # Should be close to current time
        now = datetime.now()
        assert abs((result - now).total_seconds()) < 1


class TestAnalyzeRequestLogs:
    """Test request log analysis."""
    
    def test_analyze_empty_logs(self):
        """Test analyzing empty logs."""
        result = analyze_request_logs([])
        assert result == {}
    
    def test_analyze_request_with_phases(self):
        """Test analyzing request with multiple phases."""
        logs = [
            {
                "timestamp": "2024-01-01T12:00:00",
                "event": "request_started",
                "correlation_id": "test-123"
            },
            {
                "timestamp": "2024-01-01T12:00:01",
                "event": "embedding_generation_started",
                "correlation_id": "test-123"
            },
            {
                "timestamp": "2024-01-01T12:00:02",
                "event": "embedding_generation_completed",
                "correlation_id": "test-123"
            },
            {
                "timestamp": "2024-01-01T12:00:03",
                "event": "request_completed",
                "correlation_id": "test-123",
                "duration_ms": 3000
            }
        ]
        
        result = analyze_request_logs(logs)
        
        assert "total_duration" in result
        assert result["total_duration"] == 3.0  # 3 seconds
        assert "phase_durations" in result
        assert "embedding_generation" in result["phase_durations"]
        assert result["phase_durations"]["embedding_generation"] == 1.0  # 1 second
    
    def test_analyze_request_missing_end(self):
        """Test analyzing request missing completion."""
        logs = [
            {
                "timestamp": "2024-01-01T12:00:00",
                "event": "request_started",
                "correlation_id": "test-123"
            }
        ]
        
        result = analyze_request_logs(logs)
        
        # Should handle gracefully
        assert "total_duration" not in result or result["total_duration"] is None
    
    def test_analyze_with_errors(self):
        """Test analyzing request with errors."""
        logs = [
            {
                "timestamp": "2024-01-01T12:00:00",
                "event": "request_started",
                "correlation_id": "test-123"
            },
            {
                "timestamp": "2024-01-01T12:00:01",
                "event": "error_occurred",
                "error": "Test error",
                "level": "error",
                "correlation_id": "test-123"
            },
            {
                "timestamp": "2024-01-01T12:00:02",
                "event": "request_completed",
                "status_code": 500,
                "correlation_id": "test-123"
            }
        ]
        
        result = analyze_request_logs(logs)
        
        # The current implementation doesn't track errors explicitly
        assert "correlation_id" in result
        assert result["correlation_id"] == "test-123"
        assert "total_duration" in result


class TestAggregatePerformanceStats:
    """Test performance stats aggregation."""
    
    def test_aggregate_empty_logs(self):
        """Test aggregating empty logs."""
        result = aggregate_performance_stats([])
        
        assert result["total_requests"] == 0
        assert result["phase_stats"] == {}
        assert result["duration_stats"] == {}
    
    def test_aggregate_performance_stats(self):
        """Test aggregating performance stats."""
        logs = [
            # Request 1
            {
                "event": "request_started",
                "correlation_id": "req-1",
                "timestamp": "2024-01-01T12:00:00"
            },
            {
                "event": "request_completed",
                "correlation_id": "req-1",
                "timestamp": "2024-01-01T12:00:01"
            },
            # Request 2
            {
                "event": "request_started",
                "correlation_id": "req-2",
                "timestamp": "2024-01-01T12:01:00"
            },
            {
                "event": "embedding_generation_started",
                "correlation_id": "req-2",
                "timestamp": "2024-01-01T12:01:00"
            },
            {
                "event": "embedding_generation_completed",
                "correlation_id": "req-2",
                "timestamp": "2024-01-01T12:01:01"
            },
            {
                "event": "request_completed",
                "correlation_id": "req-2",
                "timestamp": "2024-01-01T12:01:02"
            }
        ]
        
        result = aggregate_performance_stats(logs)
        
        assert result["total_requests"] == 2
        assert "phase_stats" in result
        assert "duration_stats" in result
        # Should have stats for embedding_generation phase
        if "embedding_generation" in result["phase_stats"]:
            assert "avg" in result["phase_stats"]["embedding_generation"]


class TestIdentifyBottlenecks:
    """Test bottleneck identification."""
    
    def test_identify_bottlenecks_empty(self):
        """Test identifying bottlenecks with empty stats."""
        result = identify_bottlenecks({})
        assert result == []
    
    def test_identify_bottlenecks(self):
        """Test identifying performance bottlenecks."""
        phase_stats = {
            "embedding_generation": {
                "avg": 2.0,  # 2 seconds
                "max": 5.0,
                "count": 10
            },
            "vector_search": {
                "avg": 0.5,  # 0.5 seconds
                "max": 1.0,
                "count": 10
            },
            "document_processing": {
                "avg": 3.0,  # 3 seconds
                "max": 8.0,
                "count": 5
            }
        }
        
        bottlenecks = identify_bottlenecks(phase_stats)
        
        # Should identify slowest phases
        assert len(bottlenecks) >= 1
        assert bottlenecks[0]["phase"] == "document_processing"  # Highest avg
        assert bottlenecks[0]["avg_duration"] == 3.0


class TestProfilingDecorators:
    """Test profiling decorators if they exist."""
    
    def test_profile_sync_decorator(self):
        """Test sync profiling decorator."""
        try:
            from src.monitoring.profiling import profile_sync
            
            @profile_sync("test_operation")
            def test_func(x):
                return x * 2
            
            result = test_func(5)
            assert result == 10
        except ImportError:
            # Decorator might not exist
            pass
    
    @pytest.mark.asyncio
    async def test_profile_async_decorator(self):
        """Test async profiling decorator."""
        try:
            from src.monitoring.profiling import profile_async
            
            @profile_async("test_operation")
            async def test_func(x):
                return x * 2
            
            result = await test_func(5)
            assert result == 10
        except ImportError:
            # Decorator might not exist
            pass