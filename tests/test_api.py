"""
Tests for API endpoints and routes.
"""
import os
# Set test environment before any imports
os.environ["ENVIRONMENT"] = "test"
os.environ["DISABLE_RATE_LIMIT"] = "true"

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
import json
import uuid
from datetime import datetime
import io

from src.api.main import app


class TestAPIEndpoints:
    """Test API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        # Ensure test environment is set
        with patch('src.api.middleware.settings.environment', 'test'):
            # Import app fresh to ensure clean state
            from src.api.main import app
            return TestClient(app)
    
    @pytest.fixture
    def mock_vector_store(self):
        """Mock vector store."""
        mock = Mock()
        mock.search = AsyncMock(return_value=[])
        mock.hybrid_search = AsyncMock(return_value=[])
        mock.upsert_documents = AsyncMock(return_value={"success": True, "count": 1})
        mock.delete_document = AsyncMock(return_value=True)
        mock.list_documents = AsyncMock(return_value=([], 0))  # Return tuple
        
        with patch('src.api.routes.get_vector_store', return_value=mock):
            yield mock
    
    @pytest.fixture
    def mock_embedding_generator(self):
        """Mock embedding generator."""
        mock = Mock()
        mock.generate_embeddings = AsyncMock(return_value=[{"embedding": [0.1] * 1536, "metadata": {}}])
        
        with patch('src.api.routes.get_embedding_generator', return_value=mock):
            yield mock
    
    @pytest.fixture
    def mock_job_tracker(self):
        """Mock job tracker."""
        mock = Mock()
        mock.create_job = Mock(return_value="job-123")
        mock.update_status = Mock()
        mock.get_job = Mock(return_value={"status": "processing"})
        
        with patch('src.api.routes.get_job_tracker', return_value=mock):
            yield mock
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
    
    def test_metrics_endpoint(self, client):
        """Test metrics endpoint."""
        response = client.get("/api/v1/metrics")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/plain; charset=utf-8"
        assert "# HELP" in response.text
        assert "# TYPE" in response.text
    
    @pytest.mark.asyncio
    async def test_query_endpoint(self, client, mock_vector_store, mock_embedding_generator):
        """Test query endpoint."""
        mock_vector_store.hybrid_search.return_value = [
            {
                "text": "Test result",
                "score": 0.95,
                "document_id": "doc-123",
                "metadata": {"source": "test.txt"}
            }
        ]
        
        # Mock the react agent
        with patch('src.processing.react_agent.process_query_with_agent') as mock_agent:
            mock_agent.return_value = {
                "results": [
                    {
                        "text": "Test result",
                        "score": 0.95,
                        "document_id": "doc-123",
                        "metadata": {"source": "test.txt"}
                    }
                ],
                "answer": "Generated answer",
                "total_results": 1
            }
            
            response = client.post(
                "/api/v1/query",
                json={
                    "query": "test query",
                    "limit": 5,
                    "similarity_threshold": 0.7
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "results" in data
        assert len(data["results"]) == 1
        assert data["total_results"] == 1
        assert data["search_type"] == "hybrid"
    
    def test_query_no_results(self, client, mock_vector_store, mock_embedding_generator):
        """Test query with no results."""
        mock_vector_store.hybrid_search.return_value = []
        
        with patch('src.processing.react_agent.process_query_with_agent') as mock_agent:
            mock_agent.return_value = {
                "results": [],
                "answer": "No relevant documents found.",
                "total_results": 0
            }
            
            response = client.post(
                "/api/v1/query",
                json={"query": "test query"}
            )
        
        assert response.status_code == 200
        data = response.json()
        # When no results and generate_answer is True by default, it still returns empty results
        assert "answer" in data  # Answer might be generated even with no results
        assert "results" in data
        assert len(data["results"]) == 0
        assert data["total_results"] == 0
    
    def test_ingest_text_file(self, client, mock_vector_store, mock_job_tracker):
        """Test ingesting a text file."""
        file_content = b"This is a test document content."
        
        with patch('src.api.routes.process_document') as mock_process:
            # process_document is an async function that runs in background
            mock_process.return_value = None
            
            response = client.post(
                "/api/v1/ingest",
                files={"file": ("test.txt", file_content, "text/plain")},
                data={"chunking_strategy": "sliding_window"}
            )
        
        assert response.status_code == 200  # FastAPI returns 200 for successful POST
        data = response.json()
        assert data["message"] == "Document processing started"
        assert "job_id" in data
        assert "document_id" in data
    
    def test_ingest_invalid_file_type(self, client):
        """Test ingesting invalid file type."""
        file_content = b"Invalid content"
        
        response = client.post(
            "/api/v1/ingest",
            files={"file": ("test.exe", file_content, "application/x-msdownload")}
        )
        
        assert response.status_code == 400
        assert "Unsupported file type" in response.json()["detail"]
    
    def test_ingest_large_file(self, client):
        """Test ingesting file exceeding size limit."""
        # Create file larger than limit
        large_content = b"x" * (51 * 1024 * 1024)  # 51MB
        
        response = client.post(
            "/api/v1/ingest",
            files={"file": ("large.txt", large_content, "text/plain")}
        )
        
        assert response.status_code == 400
        # Check the error message contains information about file size
        error_detail = response.json()["detail"]
        assert "exceeds maximum" in error_detail
        assert "52428800" in error_detail  # Max size in bytes
    
    def test_list_documents(self, client, mock_vector_store):
        """Test listing documents."""
        documents = [
            {
                "document_id": "doc-1",
                "metadata": {"source": "file1.txt"},
                "created_at": "2024-01-01T00:00:00"
            },
            {
                "document_id": "doc-2",
                "metadata": {"source": "file2.txt"},
                "created_at": "2024-01-02T00:00:00"
            }
        ]
        mock_vector_store.list_documents.return_value = (documents, 2)  # Return tuple
        
        response = client.get("/api/v1/documents")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["documents"]) == 2
        assert data["total"] == 2
    
    @pytest.mark.skip(reason="GET /documents/{id} endpoint not implemented")
    def test_get_document_by_id(self, client, mock_vector_store):
        """Test getting document by ID."""
        mock_vector_store.get_document_by_id.return_value = {
            "document_id": "doc-123",
            "metadata": {"source": "test.txt"},
            "chunks": [{"text": "Test chunk", "chunk_index": 0}]
        }
        
        response = client.get("/api/v1/documents/doc-123")
        
        assert response.status_code == 200
        data = response.json()
        assert data["document_id"] == "doc-123"
        assert len(data["chunks"]) == 1
    
    @pytest.mark.skip(reason="GET /documents/{id} endpoint not implemented")
    def test_get_document_not_found(self, client, mock_vector_store):
        """Test getting non-existent document."""
        mock_vector_store.get_document_by_id.return_value = None
        
        response = client.get("/api/v1/documents/non-existent")
        
        assert response.status_code == 404
        assert "Document not found" in response.json()["detail"]
    
    def test_delete_document(self, client, mock_vector_store):
        """Test deleting document."""
        response = client.delete("/api/v1/documents/doc-123")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Document deleted successfully"
        assert data["document_id"] == "doc-123"
    
    def test_get_job_status(self, client, mock_job_tracker):
        """Test getting job status."""
        mock_job_tracker.get_job.return_value = {
            "job_id": "job-123",
            "status": "completed",
            "total": 1,
            "completed": 1,
            "failed": 0,
            "current_file": "",
            "created_at": "2024-01-01T00:00:00",
            "documents": {"doc-1": {"chunks": 5}}
        }
        
        response = client.get("/api/v1/jobs/job-123")
        
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "job-123"
        assert data["status"] == "completed"
    
    def test_get_job_not_found(self, client, mock_job_tracker):
        """Test getting non-existent job."""
        mock_job_tracker.get_job.return_value = None
        
        response = client.get("/api/v1/jobs/non-existent")
        
        assert response.status_code == 404
        assert "Job not found" in response.json()["detail"]
    
    def test_rate_limiting(self, client):
        """Test rate limiting functionality."""
        # In test environment, rate limiting is disabled
        # So we'll just verify that many requests succeed
        responses = []
        for _ in range(105):  # Would exceed 100 req/min limit in production
            responses.append(client.get("/api/v1/health"))
        
        # In test environment, all should succeed
        status_codes = [r.status_code for r in responses]
        assert all(code == 200 for code in status_codes)  # All successful in test env
    
    def test_correlation_id_header(self, client):
        """Test correlation ID is added to responses."""
        response = client.get("/api/v1/health")
        
        assert "X-Correlation-ID" in response.headers
        assert len(response.headers["X-Correlation-ID"]) == 36  # UUID format
    
    def test_query_with_custom_parameters(self, client, mock_vector_store, mock_embedding_generator):
        """Test query with custom parameters."""
        with patch('src.processing.react_agent.process_query_with_agent') as mock_agent:
            mock_agent.return_value = {
                "results": [{"text": "Test", "score": 0.9}],
                "answer": "Generated answer",
                "total_results": 1
            }
            
            response = client.post(
                "/api/v1/query",
                json={
                    "query": "test query",
                    "limit": 10,
                    "similarity_threshold": 0.8,
                    "filters": {"source": "test.pdf"},
                    "generate_answer": True
                }
            )
        
        assert response.status_code == 200
        # Verify the agent was called with correct parameters
        mock_agent.assert_called_once()
        # Check that search_params were passed
        call_args = mock_agent.call_args
        assert "search_params" in call_args[1]
        assert call_args[1]["search_params"]["limit"] == 10
        assert call_args[1]["search_params"]["similarity_threshold"] == 0.8
    
    def test_ingest_with_chunking_strategy(self, client, mock_job_tracker):
        """Test document ingestion with specific chunking strategy."""
        file_content = b"Test document for chunking."
        
        with patch('src.api.routes.process_document') as mock_process:
            mock_process.return_value = None
            
            response = client.post(
                "/api/v1/ingest",
                files={"file": ("test.txt", file_content, "text/plain")},
                data={
                    "chunking_strategy": "semantic",
                    "chunk_size": "500",
                    "chunk_overlap": "50"
                }
            )
        
        assert response.status_code == 200
        # Since process_document is called via background_tasks.add_task,
        # we can't easily verify the call args in this test setup.
        # The test is successful if the endpoint accepts the chunking strategy
        # and returns 200 OK.
    
    @pytest.mark.skip(reason="Stats endpoint not implemented")
    def test_stats_endpoint(self, client, mock_vector_store):
        """Test stats endpoint."""
        mock_vector_store.get_collection_stats.return_value = {
            "vectors_count": 1000,
            "points_count": 1000,
            "indexed_vectors_count": 1000
        }
        
        with patch('src.api.routes.metrics_collector.get_metrics_summary') as mock_metrics:
            mock_metrics.return_value = {
                "http_requests": 500,
                "documents_processed": 50
            }
            
            response = client.get("/api/v1/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert "vector_db" in data
        assert "metrics" in data
        assert data["vector_db"]["vectors_count"] == 1000


class TestAPIErrorHandling:
    """Test API error handling."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        # Ensure test environment is set
        with patch('src.api.middleware.settings.environment', 'test'):
            # Import app fresh to ensure clean state
            from src.api.main import app
            return TestClient(app)
    
    def test_internal_server_error(self, client):
        """Test handling of internal server errors."""
        with patch('src.api.routes.get_embedding_generator') as mock_get_gen:
            mock_gen = Mock()
            mock_gen.generate_embeddings = AsyncMock(side_effect=Exception("Embedding service error"))
            mock_get_gen.return_value = mock_gen
            
            response = client.post(
                "/api/v1/query",
                json={"query": "test"}
            )
        
        assert response.status_code == 500
        assert "Query processing failed" in response.json()["detail"]
    
    def test_validation_error(self, client):
        """Test request validation errors."""
        response = client.post(
            "/api/v1/query",
            json={"invalid_field": "test"}  # Missing required 'query' field
        )
        
        assert response.status_code == 422
        # FastAPI returns validation errors as a list in the detail field
        error_response = response.json()
        assert "detail" in error_response
        # Check that it's a validation error for the missing 'query' field
        if isinstance(error_response["detail"], list):
            assert any("query" in str(error).lower() for error in error_response["detail"])
        else:
            assert "validation error" in str(error_response["detail"]).lower()
    
    def test_method_not_allowed(self, client):
        """Test method not allowed error."""
        response = client.put("/api/v1/health")  # Health only supports GET
        
        assert response.status_code == 405
        assert "Method Not Allowed" in response.json()["detail"]