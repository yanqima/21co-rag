"""
Additional tests for API routes to increase coverage.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
import json
import io

from src.api.main import app


class TestRoutesAdditional:
    """Additional route tests for better coverage."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_dependencies(self):
        """Mock all route dependencies."""
        with patch('src.api.routes.get_vector_store') as mock_vector_store:
            with patch('src.api.routes.get_embedding_generator') as mock_embedding:
                with patch('src.api.routes.get_document_validator') as mock_validator:
                    with patch('src.api.routes.get_job_tracker') as mock_job_tracker:
                        # Set up vector store
                        vs = Mock()
                        vs.search = AsyncMock(return_value=[])
                        vs.hybrid_search = AsyncMock(return_value=[])
                        vs.upsert_documents = AsyncMock(return_value=["doc-1"])
                        vs.delete_document = AsyncMock(return_value=True)
                        vs.list_documents = AsyncMock(return_value=([], 0))
                        mock_vector_store.return_value = vs
                        
                        # Set up embedding generator
                        eg = Mock()
                        eg.generate_embeddings = AsyncMock(return_value=[
                            {"embedding": [0.1] * 1536, "metadata": {}}
                        ])
                        mock_embedding.return_value = eg
                        
                        # Set up validator
                        val = Mock()
                        val.validate_file = Mock(return_value={
                            "file_type": "txt",
                            "filename": "test.txt",
                            "file_hash": "abc123"
                        })
                        val.validate_content = Mock()
                        mock_validator.return_value = val
                        
                        # Set up job tracker
                        jt = Mock()
                        jt.create_job = Mock(return_value="job-123")
                        jt.get_job = Mock(return_value={
                            "job_id": "job-123",
                            "status": "processing",
                            "total": 1,
                            "completed": 0,
                            "failed": 0,
                            "current_file": "test.txt",
                            "created_at": "2024-01-01T00:00:00",
                            "documents": {}
                        })
                        jt.update_job_progress = Mock()
                        mock_job_tracker.return_value = jt
                        
                        yield {
                            "vector_store": vs,
                            "embedding_generator": eg,
                            "validator": val,
                            "job_tracker": jt
                        }
    
    def test_batch_ingest_no_files(self, client, mock_dependencies):
        """Test batch ingest with no files."""
        response = client.post("/api/v1/batch-ingest")
        
        assert response.status_code == 422  # Validation error
    
    def test_batch_ingest_too_many_files(self, client, mock_dependencies):
        """Test batch ingest with too many files."""
        # Create 101 dummy files
        files = []
        for i in range(101):
            files.append(
                ("files", (f"file{i}.txt", b"content", "text/plain"))
            )
        
        response = client.post("/api/v1/batch-ingest", files=files)
        
        assert response.status_code == 400
        assert "Maximum 100 files" in response.json()["detail"]
    
    def test_batch_ingest_success(self, client, mock_dependencies):
        """Test successful batch ingest."""
        files = [
            ("files", ("file1.txt", b"content1", "text/plain")),
            ("files", ("file2.txt", b"content2", "text/plain"))
        ]
        
        with patch('src.api.routes.process_batch_documents'):
            response = client.post(
                "/api/v1/batch-ingest",
                files=files,
                data={"chunking_strategy": "sliding_window"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "job-123"
        assert data["total_files"] == 2
    
    def test_get_logs_with_correlation_id(self, client):
        """Test getting logs with correlation ID."""
        with patch('redis.Redis') as mock_redis_class:
            mock_redis = Mock()
            mock_redis_class.return_value = mock_redis
            
            # Mock correlation-specific logs
            mock_redis.lrange.return_value = ["logs:123", "logs:124"]
            mock_redis.get.side_effect = [
                json.dumps({
                    "timestamp": "2024-01-01T00:00:00",
                    "level": "info",
                    "event": "test_event",
                    "correlation_id": "test-corr-id"
                }),
                json.dumps({
                    "timestamp": "2024-01-01T00:01:00",
                    "level": "info",
                    "event": "test_event2",
                    "correlation_id": "test-corr-id"
                })
            ]
            
            response = client.get("/api/v1/logs?correlation_id=test-corr-id")
            
            assert response.status_code == 200
            data = response.json()
            assert data["count"] == 2
            assert data["filtered_by"] == "correlation_id: test-corr-id"
    
    def test_get_logs_with_level_filter(self, client):
        """Test getting logs with level filter."""
        with patch('redis.Redis') as mock_redis_class:
            mock_redis = Mock()
            mock_redis_class.return_value = mock_redis
            
            mock_redis.lrange.return_value = ["logs:123", "logs:124"]
            mock_redis.get.side_effect = [
                json.dumps({
                    "timestamp": "2024-01-01T00:00:00",
                    "level": "error",
                    "event": "test_error"
                }),
                json.dumps({
                    "timestamp": "2024-01-01T00:01:00",
                    "level": "info",
                    "event": "test_info"
                })
            ]
            
            response = client.get("/api/v1/logs?level=error")
            
            assert response.status_code == 200
            data = response.json()
            assert data["count"] == 1
            assert data["logs"][0]["level"] == "error"
    
    def test_get_profiling_stats(self, client):
        """Test getting profiling statistics."""
        with patch('redis.Redis') as mock_redis_class:
            mock_redis = Mock()
            mock_redis_class.return_value = mock_redis
            
            # Mock log data for profiling
            mock_redis.lrange.return_value = ["logs:1", "logs:2"]
            mock_redis.get.side_effect = [
                json.dumps({
                    "timestamp": "2024-01-01T00:00:00.123",
                    "event": "embeddings_generation_started",
                    "correlation_id": "test-1"
                }),
                json.dumps({
                    "timestamp": "2024-01-01T00:00:01.456",
                    "event": "embeddings_generation_completed",
                    "correlation_id": "test-1",
                    "duration": 1.333
                })
            ]
            
            response = client.get("/api/v1/profiling")
            
            assert response.status_code == 200
            data = response.json()
            assert "stats" in data
            assert "bottlenecks" in data
            assert "timestamp" in data
    
    def test_process_document_pdf(self, mock_dependencies):
        """Test processing PDF document."""
        from src.api.routes import process_document
        
        with patch('src.api.routes.extract_pdf_text') as mock_extract:
            mock_extract.return_value = "PDF content"
            
            validation_result = {
                "file_type": "pdf",
                "filename": "test.pdf",
                "file_hash": "abc123"
            }
            
            # Run async function
            import asyncio
            asyncio.run(process_document(
                file_content=b"fake pdf content",
                document_id="doc-123",
                validation_result=validation_result,
                chunking_strategy="sliding_window",
                chunk_size=None,
                chunk_overlap=None,
                correlation_id="test-corr"
            ))
            
            mock_extract.assert_called_once()
    
    def test_process_document_json(self, mock_dependencies):
        """Test processing JSON document."""
        from src.api.routes import process_document
        
        validation_result = {
            "file_type": "json",
            "filename": "test.json",
            "file_hash": "abc123"
        }
        
        json_content = json.dumps({"key": "value"}).encode()
        
        # Run async function
        import asyncio
        asyncio.run(process_document(
            file_content=json_content,
            document_id="doc-123",
            validation_result=validation_result,
            chunking_strategy="sliding_window",
            chunk_size=None,
            chunk_overlap=None,
            correlation_id="test-corr"
        ))
    
    def test_query_without_answer_generation(self, client, mock_dependencies):
        """Test query endpoint without answer generation."""
        mock_dependencies["vector_store"].hybrid_search.return_value = [
            {
                "text": "Test result",
                "score": 0.9,
                "metadata": {"source": "test.txt"}
            }
        ]
        
        response = client.post(
            "/api/v1/query",
            json={
                "query": "test query",
                "generate_answer": False
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["answer"] is None
        assert len(data["results"]) == 1
    
    def test_delete_document_not_found(self, client, mock_dependencies):
        """Test deleting non-existent document."""
        mock_dependencies["vector_store"].delete_document.return_value = False
        
        response = client.delete("/api/v1/documents/non-existent")
        
        assert response.status_code == 404
        assert "Document not found" in response.json()["detail"]
    
    def test_get_job_not_found(self, client, mock_dependencies):
        """Test getting non-existent job."""
        mock_dependencies["job_tracker"].get_job.return_value = None
        
        response = client.get("/api/v1/jobs/non-existent")
        
        assert response.status_code == 404
        assert "Job not found" in response.json()["detail"]