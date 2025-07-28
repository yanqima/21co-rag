"""
Pytest configuration and fixtures for the RAG system tests.
"""
import os
import sys
import pytest
import asyncio
from unittest.mock import Mock, patch
from typing import Generator, Any
import time
from functools import wraps

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def retry_on_openai_error(max_retries: int = 3, delay: float = 1.0):
    """
    Decorator to retry tests that might fail due to OpenAI API rate limits.
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if "rate limit" in str(e).lower() or "openai" in str(e).lower():
                        if attempt < max_retries - 1:
                            await asyncio.sleep(delay * (attempt + 1))
                            continue
                    raise
            return await func(*args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if "rate limit" in str(e).lower() or "openai" in str(e).lower():
                        if attempt < max_retries - 1:
                            time.sleep(delay * (attempt + 1))
                            continue
                    raise
            return func(*args, **kwargs)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing."""
    with patch('openai.OpenAI') as mock:
        client = Mock()
        mock.return_value = client
        
        # Mock embeddings
        embeddings_response = Mock()
        embeddings_response.data = [Mock(embedding=[0.1] * 1536)]
        client.embeddings.create.return_value = embeddings_response
        
        # Mock chat completions
        completion_response = Mock()
        completion_response.choices = [
            Mock(message=Mock(content="Mocked response"))
        ]
        client.chat.completions.create.return_value = completion_response
        
        yield client


@pytest.fixture
def mock_qdrant_client():
    """Mock Qdrant client for testing."""
    with patch('qdrant_client.QdrantClient') as mock:
        client = Mock()
        mock.return_value = client
        
        # Mock common operations
        client.create_collection.return_value = True
        client.upsert.return_value = Mock(status="ok")
        client.search.return_value = [
            Mock(
                id="test-id",
                score=0.9,
                payload={
                    "text": "Test content",
                    "metadata": {"source": "test"}
                }
            )
        ]
        
        yield client


@pytest.fixture
def sample_document():
    """Sample document for testing."""
    return {
        "content": "This is a sample document for testing purposes. It contains multiple sentences.",
        "metadata": {
            "source": "test.txt",
            "document_id": "test-123",
            "created_at": "2024-07-28T12:00:00Z"
        }
    }


@pytest.fixture
def sample_chunks():
    """Sample chunks for testing."""
    return [
        {
            "text": "This is a sample document",
            "chunk_id": "chunk-1",
            "metadata": {"source": "test.txt"}
        },
        {
            "text": "for testing purposes.",
            "chunk_id": "chunk-2",
            "metadata": {"source": "test.txt"}
        }
    ]


@pytest.fixture
async def async_client():
    """Fixture for async HTTP client."""
    from httpx import AsyncClient
    from src.api.main import app
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def temp_upload_file(tmp_path):
    """Create a temporary file for upload testing."""
    file_path = tmp_path / "test.txt"
    file_path.write_text("Test content for upload")
    return file_path


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    with patch('redis.Redis') as mock:
        client = Mock()
        mock.from_url.return_value = client
        
        # Mock common operations
        client.get.return_value = None
        client.set.return_value = True
        client.delete.return_value = 1
        client.lpush.return_value = 1
        client.brpop.return_value = (b'queue', b'{"task": "test"}')
        
        yield client


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set environment variables for testing."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("QDRANT_HOST", "localhost")
    monkeypatch.setenv("QDRANT_PORT", "6333")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    monkeypatch.setenv("ENVIRONMENT", "test")