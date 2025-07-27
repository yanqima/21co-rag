import pytest
from fastapi.testclient import TestClient
from src.api.main import app
import os

client = TestClient(app)


def test_root_endpoint():
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["message"] == "RAG API is running"


def test_health_endpoint():
    """Test health check endpoint."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_metrics_endpoint():
    """Test metrics endpoint."""
    response = client.get("/api/v1/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/plain; charset=utf-8"


def test_ingest_invalid_file():
    """Test document ingestion with invalid file."""
    response = client.post("/api/v1/ingest")
    assert response.status_code == 422  # Unprocessable Entity


def test_query_endpoint():
    """Test query endpoint."""
    query_data = {
        "query": "What is machine learning?",
        "limit": 5,
        "similarity_threshold": 0.7,
        "search_type": "hybrid",
        "generate_answer": False
    }
    response = client.post("/api/v1/query", json=query_data)
    # Should work but return empty results since no documents are indexed
    assert response.status_code == 200
    assert response.json()["total_results"] == 0


def test_list_documents():
    """Test list documents endpoint."""
    response = client.get("/api/v1/documents")
    assert response.status_code == 200
    assert "documents" in response.json()
    assert "total" in response.json()


def test_delete_nonexistent_document():
    """Test deleting a non-existent document."""
    response = client.delete("/api/v1/documents/nonexistent-id")
    # Should return 404 or handle gracefully
    assert response.status_code in [404, 200]


@pytest.mark.skipif(not os.path.exists("sample_data/sample_document.txt"), 
                    reason="Sample file not found")
def test_ingest_text_file():
    """Test ingesting a text file."""
    with open("sample_data/sample_document.txt", "rb") as f:
        files = {"file": ("sample_document.txt", f, "text/plain")}
        response = client.post("/api/v1/ingest", files=files)
    
    assert response.status_code == 200
    assert "job_id" in response.json()
    assert "document_id" in response.json()