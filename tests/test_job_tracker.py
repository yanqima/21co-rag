"""
Tests for the job tracker module.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import json
import uuid
from datetime import datetime

from src.processing.job_tracker import JobTracker


class TestJobTracker:
    """Test JobTracker class."""
    
    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis client."""
        with patch('redis.Redis') as mock_redis_class:
            mock_client = Mock()
            mock_redis_class.return_value = mock_client
            yield mock_client
    
    @pytest.fixture
    def job_tracker(self, mock_redis):
        """Create JobTracker instance with mocked Redis."""
        tracker = JobTracker()
        return tracker
    
    def test_create_job(self, job_tracker, mock_redis):
        """Test creating a new job."""
        with patch('uuid.uuid4', return_value='test-job-id'):
            job_id = job_tracker.create_job(total_documents=5)
        
        assert job_id == 'test-job-id'
        
        # Check Redis was called correctly
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        
        # Check key format
        assert call_args[0][0] == 'job:test-job-id'
        assert call_args[0][1] == 86400  # TTL
        
        # Check job data
        job_data = json.loads(call_args[0][2])
        assert job_data['job_id'] == 'test-job-id'
        assert job_data['status'] == 'processing'
        assert job_data['total'] == 5
        assert job_data['completed'] == 0
        assert job_data['failed'] == 0
    
    def test_get_job(self, job_tracker, mock_redis):
        """Test getting job by ID."""
        job_data = {
            "job_id": "test-job-id",
            "status": "processing",
            "total": 5,
            "completed": 2
        }
        mock_redis.get.return_value = json.dumps(job_data)
        
        result = job_tracker.get_job("test-job-id")
        
        assert result == job_data
        mock_redis.get.assert_called_with("job:test-job-id")
    
    def test_get_nonexistent_job(self, job_tracker, mock_redis):
        """Test getting non-existent job."""
        mock_redis.get.return_value = None
        
        result = job_tracker.get_job("non-existent")
        
        assert result is None
    
    def test_update_job_progress_completed(self, job_tracker, mock_redis):
        """Test updating job progress with completed document."""
        job_data = {
            "job_id": "test-job-id",
            "status": "processing",
            "total": 3,
            "completed": 1,
            "failed": 0,
            "current_file": "",
            "documents": {}
        }
        mock_redis.get.return_value = json.dumps(job_data)
        
        job_tracker.update_job_progress(
            job_id="test-job-id",
            current_file="doc2.txt",
            document_id="doc-2",
            status="completed"
        )
        
        # Check Redis was updated
        mock_redis.setex.assert_called()
        updated_data = json.loads(mock_redis.setex.call_args[0][2])
        
        assert updated_data["completed"] == 2
        assert updated_data["current_file"] == "doc2.txt"
        assert "doc-2" in updated_data["documents"]
        assert updated_data["documents"]["doc-2"]["status"] == "completed"
    
    def test_update_job_progress_failed(self, job_tracker, mock_redis):
        """Test updating job progress with failed document."""
        job_data = {
            "job_id": "test-job-id",
            "status": "processing",
            "total": 3,
            "completed": 1,
            "failed": 0,
            "current_file": "",
            "documents": {}
        }
        mock_redis.get.return_value = json.dumps(job_data)
        
        job_tracker.update_job_progress(
            job_id="test-job-id",
            current_file="doc2.txt",
            document_id="doc-2",
            status="failed",
            error="Processing error"
        )
        
        updated_data = json.loads(mock_redis.setex.call_args[0][2])
        
        assert updated_data["failed"] == 1
        assert updated_data["documents"]["doc-2"]["status"] == "failed"
        assert updated_data["documents"]["doc-2"]["error"] == "Processing error"
    
    def test_update_job_progress_completes_job(self, job_tracker, mock_redis):
        """Test that job is marked complete when all documents processed."""
        job_data = {
            "job_id": "test-job-id",
            "status": "processing",
            "total": 2,
            "completed": 1,
            "failed": 0,
            "current_file": "doc1.txt",
            "documents": {"doc-1": {"status": "completed"}}
        }
        mock_redis.get.return_value = json.dumps(job_data)
        
        job_tracker.update_job_progress(
            job_id="test-job-id",
            current_file="doc2.txt",
            document_id="doc-2",
            status="completed"
        )
        
        updated_data = json.loads(mock_redis.setex.call_args[0][2])
        
        assert updated_data["status"] == "completed"
        assert updated_data["completed"] == 2
        assert updated_data["current_file"] == ""
    
    def test_mark_job_failed(self, job_tracker, mock_redis):
        """Test marking entire job as failed."""
        job_data = {
            "job_id": "test-job-id",
            "status": "processing",
            "total": 5,
            "completed": 2
        }
        mock_redis.get.return_value = json.dumps(job_data)
        
        job_tracker.mark_job_failed("test-job-id", "Critical error occurred")
        
        updated_data = json.loads(mock_redis.setex.call_args[0][2])
        
        assert updated_data["status"] == "failed"
        assert updated_data["error"] == "Critical error occurred"
    
    def test_job_ttl_configuration(self, job_tracker):
        """Test job TTL configuration."""
        assert job_tracker.job_ttl == 86400  # 24 hours
    
    def test_update_nonexistent_job(self, job_tracker, mock_redis):
        """Test updating non-existent job logs error."""
        mock_redis.get.return_value = None
        
        # Should not raise exception
        job_tracker.update_job_progress(
            job_id="non-existent",
            current_file="test.txt",
            document_id="doc-1",
            status="completed"
        )
        
        # Should not try to save
        assert mock_redis.setex.call_count == 0
    
    def test_create_job_generates_unique_ids(self, job_tracker, mock_redis):
        """Test that each job gets a unique ID."""
        # Create multiple jobs
        job_id1 = job_tracker.create_job(total_documents=1)
        job_id2 = job_tracker.create_job(total_documents=1)
        
        assert job_id1 != job_id2
        assert len(job_id1) == 36  # UUID format
        assert len(job_id2) == 36
    
    def test_job_data_serialization(self, job_tracker, mock_redis):
        """Test job data is properly serialized/deserialized."""
        # Create job with complex data
        job_id = job_tracker.create_job(total_documents=2)
        
        # Get the serialized data
        call_args = mock_redis.setex.call_args[0]
        serialized_data = call_args[2]
        
        # Should be valid JSON
        deserialized = json.loads(serialized_data)
        assert isinstance(deserialized, dict)
        assert "created_at" in deserialized
        assert "documents" in deserialized
        assert isinstance(deserialized["documents"], dict)