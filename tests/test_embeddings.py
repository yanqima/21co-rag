"""
Tests for the embeddings module.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock, PropertyMock, MagicMock
import numpy as np
import asyncio

from src.processing.embeddings import EmbeddingGenerator
from src.config import settings


class TestEmbeddingGenerator:
    """Test EmbeddingGenerator class."""
    
    @pytest.fixture
    def mock_httpx_client(self):
        """Mock httpx for OpenAI API calls."""
        with patch('httpx.AsyncClient') as mock_class:
            mock_client = MagicMock()
            mock_instance = MagicMock()
            mock_class.return_value.__aenter__.return_value = mock_instance
            mock_class.return_value.__aexit__.return_value = None
            
            # Create mock response
            async def mock_post(*args, **kwargs):
                data = kwargs.get('json', {})
                input_texts = data.get('input', [])
                
                mock_embeddings = []
                for i, text in enumerate(input_texts):
                    mock_embeddings.append({
                        "embedding": [0.1 * (i + 1)] * 1536,
                        "index": i
                    })
                
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "data": mock_embeddings
                }
                return mock_response
            
            mock_instance.post = mock_post
            yield mock_instance
    
    @pytest.fixture
    def embedding_generator(self, mock_httpx_client):
        """Create EmbeddingGenerator instance with mocked dependencies."""
        with patch('src.processing.embeddings.settings') as mock_settings:
            mock_settings.embedding_model = "text-embedding-ada-002"
            mock_settings.batch_size = 32
            mock_settings.openai_api_key = "test-key"
            
            generator = EmbeddingGenerator()
            # Force the model to be OpenAI
            generator._model = "openai"
            return generator
    
    @pytest.mark.asyncio
    async def test_generate_single_embedding(self, embedding_generator):
        """Test generating embedding for single text."""
        results = await embedding_generator.generate_embeddings(["test text"])
        
        assert len(results) == 1
        assert results[0]["text"] == "test text"
        assert len(results[0]["embedding"]) == 1536
        assert results[0]["metadata"] == {}
        assert all(isinstance(x, float) for x in results[0]["embedding"])
    
    @pytest.mark.asyncio
    async def test_generate_batch_embeddings(self, embedding_generator):
        """Test generating embeddings for multiple texts."""
        texts = ["text 1", "text 2", "text 3"]
        
        results = await embedding_generator.generate_embeddings(texts)
        
        assert len(results) == 3
        assert all(len(res["embedding"]) == 1536 for res in results)
        assert [res["text"] for res in results] == texts
    
    @pytest.mark.asyncio
    async def test_generate_empty_text(self, embedding_generator):
        """Test handling empty text."""
        embeddings = await embedding_generator.generate_embeddings([])
        assert embeddings == []
    
    @pytest.mark.asyncio
    async def test_generate_with_metadata(self, embedding_generator):
        """Test generating embeddings with metadata."""
        texts = ["text 1", "text 2"]
        metadata = [{"source": "doc1"}, {"source": "doc2"}]
        
        results = await embedding_generator.generate_embeddings(texts, metadata)
        
        assert len(results) == 2
        assert results[0]["metadata"] == {"source": "doc1"}
        assert results[1]["metadata"] == {"source": "doc2"}
    
    @pytest.mark.asyncio
    async def test_error_handling(self, embedding_generator):
        """Test error handling in embedding generation."""
        with patch('httpx.AsyncClient') as mock_class:
            mock_instance = MagicMock()
            mock_class.return_value.__aenter__.return_value = mock_instance
            mock_class.return_value.__aexit__.return_value = None
            
            # Make post raise an exception
            mock_instance.post = AsyncMock(side_effect=Exception("API Error"))
            
            # The retry decorator will retry 3 times, so we expect it to eventually fail
            with pytest.raises(Exception):
                await embedding_generator.generate_embeddings(["test text"])
    
    @pytest.mark.asyncio
    async def test_large_batch_processing(self, embedding_generator):
        """Test processing large batches of text."""
        # Create 100 texts
        texts = [f"text {i}" for i in range(100)]
        
        results = await embedding_generator.generate_embeddings(texts)
        
        assert len(results) == 100
        assert all(len(res["embedding"]) == 1536 for res in results)
        assert all(res["text"] == f"text {i}" for i, res in enumerate(results))
    
    def test_model_configuration(self, embedding_generator):
        """Test model configuration."""
        assert embedding_generator.model_name == "text-embedding-ada-002"
        assert embedding_generator.batch_size == 32
        assert embedding_generator.model == "openai"
    
    @pytest.mark.asyncio 
    async def test_async_generation(self, embedding_generator):
        """Test async embedding generation."""
        texts = ["async text 1", "async text 2"]
        
        # Run multiple generations concurrently
        results = await asyncio.gather(
            embedding_generator.generate_embeddings([texts[0]]),
            embedding_generator.generate_embeddings([texts[1]])
        )
        
        assert len(results) == 2
        assert results[0][0]["text"] == "async text 1"
        assert results[1][0]["text"] == "async text 2"
    
    @pytest.mark.asyncio
    async def test_embedding_dimension_validation(self, embedding_generator):
        """Test that embeddings have correct dimensions."""
        results = await embedding_generator.generate_embeddings(["test"])
        
        assert len(results[0]["embedding"]) == 1536
        # Check it's a list of floats
        assert all(isinstance(x, (int, float)) for x in results[0]["embedding"])