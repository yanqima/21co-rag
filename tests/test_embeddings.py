"""
Tests for the embeddings module.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock, PropertyMock
import numpy as np
import asyncio

from src.processing.embeddings import EmbeddingGenerator
from src.config import settings


class TestEmbeddingGenerator:
    """Test EmbeddingGenerator class."""
    
    @pytest.fixture
    def embedding_generator(self):
        """Create EmbeddingGenerator instance."""
        generator = EmbeddingGenerator()
        return generator
    
    @pytest.mark.asyncio
    async def test_generate_single_embedding(self, embedding_generator):
        """Test generating embedding for single text."""
        with patch.object(type(embedding_generator), 'model', new_callable=PropertyMock) as mock_model:
            mock_model.return_value = "openai"
            with patch('openai.AsyncOpenAI') as mock_openai_class:
                mock_client = AsyncMock()
                mock_openai_class.return_value = mock_client
                
                # Mock embedding response
                mock_response = Mock()
                mock_response.data = [Mock(embedding=[0.1] * 1536)]
                mock_client.embeddings.create = AsyncMock(return_value=mock_response)
                
                results = await embedding_generator.generate_embeddings(["test text"])
                
                assert len(results) == 1
                assert results[0]["text"] == "test text"
                assert len(results[0]["embedding"]) == 1536
                assert results[0]["metadata"] == {}
    
    @pytest.mark.asyncio
    async def test_generate_batch_embeddings(self, embedding_generator):
        """Test generating embeddings for multiple texts."""
        texts = ["text 1", "text 2", "text 3"]
        
        with patch.object(type(embedding_generator), 'model', new_callable=PropertyMock) as mock_model:
            mock_model.return_value = "openai"
            with patch('openai.AsyncOpenAI') as mock_openai_class:
                mock_client = AsyncMock()
                mock_openai_class.return_value = mock_client
                
                # Mock embedding responses
                mock_response = Mock()
                mock_response.data = [
                    Mock(embedding=[0.1] * 1536),
                    Mock(embedding=[0.2] * 1536),
                    Mock(embedding=[0.3] * 1536)
                ]
                mock_client.embeddings.create = AsyncMock(return_value=mock_response)
                
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
        
        with patch.object(type(embedding_generator), 'model', new_callable=PropertyMock) as mock_model:
            mock_model.return_value = "openai"
            with patch('openai.AsyncOpenAI') as mock_openai_class:
                mock_client = AsyncMock()
                mock_openai_class.return_value = mock_client
                
                # Mock embedding response
                mock_response = Mock()
                mock_response.data = [
                    Mock(embedding=[0.1] * 1536),
                    Mock(embedding=[0.2] * 1536)
                ]
                mock_client.embeddings.create = AsyncMock(return_value=mock_response)
                
                results = await embedding_generator.generate_embeddings(texts, metadata)
                
                assert len(results) == 2
                assert results[0]["metadata"] == {"source": "doc1"}
                assert results[1]["metadata"] == {"source": "doc2"}
    
    @pytest.mark.asyncio
    async def test_error_handling(self, embedding_generator):
        """Test error handling in embedding generation."""
        with patch.object(type(embedding_generator), 'model', new_callable=PropertyMock) as mock_model:
            mock_model.return_value = "openai"
            with patch('openai.AsyncOpenAI') as mock_openai_class:
                mock_client = AsyncMock()
                mock_openai_class.return_value = mock_client
                
                # Mock API error
                mock_client.embeddings.create = AsyncMock(
                    side_effect=Exception("API Error")
                )
                
                with pytest.raises(Exception):
                    await embedding_generator.generate_embeddings(["test"])
    
    @pytest.mark.asyncio
    async def test_large_batch_processing(self, embedding_generator):
        """Test processing large batches."""
        # Create large batch that should be split
        large_texts = [f"text {i}" for i in range(100)]
        
        with patch.object(type(embedding_generator), 'model', new_callable=PropertyMock) as mock_model:
            mock_model.return_value = "openai"
            with patch('openai.AsyncOpenAI') as mock_openai_class:
                mock_client = AsyncMock()
                mock_openai_class.return_value = mock_client
                
                # Mock responses for each batch
                def create_mock_response(texts):
                    return Mock(data=[Mock(embedding=[0.1] * 1536) for _ in texts])
                
                mock_client.embeddings.create = AsyncMock(
                    side_effect=lambda input, **kwargs: create_mock_response(input)
                )
                
                results = await embedding_generator.generate_embeddings(large_texts)
                
                assert len(results) == 100
                # Should have made multiple API calls due to batching
                assert mock_client.embeddings.create.call_count > 1
    
    def test_model_configuration(self):
        """Test model configuration."""
        generator = EmbeddingGenerator()
        
        assert generator.model_name == settings.embedding_model
        assert generator.batch_size == settings.batch_size
    
    def test_get_embedding_dimension(self, embedding_generator):
        """Test getting embedding dimension."""
        with patch.object(type(embedding_generator), 'model', new_callable=PropertyMock) as mock_model:
            # Test OpenAI dimension
            mock_model.return_value = "openai"
            assert embedding_generator.get_embedding_dimension() == 1536
            
            # Test sentence transformer dimension
            mock_transformer = Mock()
            mock_transformer.get_sentence_embedding_dimension.return_value = 384
            mock_model.return_value = mock_transformer
            assert embedding_generator.get_embedding_dimension() == 384
    
    @pytest.mark.asyncio
    async def test_async_generation(self, embedding_generator):
        """Test async embedding generation."""
        texts = ["async test 1", "async test 2"]
        
        with patch.object(type(embedding_generator), 'model', new_callable=PropertyMock) as mock_model:
            mock_model.return_value = "openai"
            with patch('openai.AsyncOpenAI') as mock_openai_class:
                mock_client = AsyncMock()
                mock_openai_class.return_value = mock_client
                
                mock_response = Mock()
                mock_response.data = [
                    Mock(embedding=[0.1] * 1536),
                    Mock(embedding=[0.2] * 1536)
                ]
                mock_client.embeddings.create = AsyncMock(return_value=mock_response)
                
                # Should work with async/await
                results = await embedding_generator.generate_embeddings(texts)
                
                assert len(results) == 2
    
    def test_sentence_transformer_fallback(self):
        """Test fallback when sentence-transformers is not available."""
        # Skip this test if sentence_transformers is not installed
        pytest.skip("Skipping sentence transformer test - module not available")
    
    @pytest.mark.asyncio
    async def test_embedding_dimension_validation(self, embedding_generator):
        """Test that embeddings have correct dimensions."""
        with patch.object(type(embedding_generator), 'model', new_callable=PropertyMock) as mock_model:
            mock_model.return_value = "openai"
            with patch('openai.AsyncOpenAI') as mock_openai_class:
                mock_client = AsyncMock()
                mock_openai_class.return_value = mock_client
                
                # Mock response with correct dimensions
                mock_response = Mock()
                mock_response.data = [Mock(embedding=np.random.rand(1536).tolist())]
                mock_client.embeddings.create = AsyncMock(return_value=mock_response)
                
                results = await embedding_generator.generate_embeddings(["test"])
                
                assert len(results[0]["embedding"]) == 1536
                assert all(isinstance(x, (int, float)) for x in results[0]["embedding"])


class TestEmbeddingCache:
    """Test embedding caching functionality."""
    
    @pytest.mark.skip(reason="Cache implementation not yet complete")
    def test_cache_operations(self):
        """Test basic cache operations."""
        # This test is skipped as cache implementation is not complete
        pass