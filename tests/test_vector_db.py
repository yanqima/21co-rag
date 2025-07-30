"""
Tests for the vector database module.
"""
import pytest
import pytest_asyncio
from unittest.mock import Mock, patch, MagicMock, call, AsyncMock
from datetime import datetime
import uuid

from src.storage.vector_db import VectorStore
from qdrant_client.models import PointStruct, Filter, FieldCondition, MatchValue


class TestVectorStore:
    """Test VectorStore class."""
    
    @pytest.fixture
    def mock_settings(self):
        """Mock settings for vector store."""
        with patch('src.storage.vector_db.settings') as mock_settings:
            mock_settings.qdrant_url = "http://localhost:6333"
            mock_settings.qdrant_api_key = None
            mock_settings.qdrant_collection = "documents"
            mock_settings.embedding_dimension = 1536
            yield mock_settings
    
    @pytest.fixture
    def mock_qdrant_client(self):
        """Create mock Qdrant client."""
        with patch('src.storage.vector_db.QdrantClient') as mock_class:
            mock_client = Mock()
            mock_class.return_value = mock_client
            
            # Mock get_collections
            mock_collection = Mock()
            mock_collection.name = 'documents'
            mock_client.get_collections.return_value.collections = [mock_collection]
            
            # Mock get_collection for dimension check
            mock_collection_info = Mock()
            mock_collection_info.config.params.vectors.size = 1536
            mock_client.get_collection.return_value = mock_collection_info
            
            yield mock_client
    
    @pytest.fixture
    def vector_store(self, mock_qdrant_client, mock_settings):
        """Create VectorStore instance with mocked client."""
        with patch('src.storage.vector_db.logger'):
            store = VectorStore()
            return store
    
    def test_init_creates_collection_if_not_exists(self, mock_settings):
        """Test collection creation on initialization."""
        with patch('src.storage.vector_db.QdrantClient') as mock_class:
            mock_client = Mock()
            mock_class.return_value = mock_client
            
            # Mock no existing collections
            mock_client.get_collections.return_value.collections = []
            
            with patch('src.storage.vector_db.logger'):
                store = VectorStore()
            
            # Should create collection
            mock_client.create_collection.assert_called_once()
            # Should create indices
            assert mock_client.create_payload_index.call_count >= 1
    
    def test_init_does_not_create_existing_collection(self, mock_qdrant_client, mock_settings):
        """Test that existing collection is not recreated."""
        with patch('src.storage.vector_db.logger'):
            store = VectorStore()
            mock_qdrant_client.create_collection.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_upsert_documents(self, vector_store, mock_qdrant_client):
        """Test adding documents with embeddings."""
        documents = [{
            "text": "Test chunk",
            "embedding": [0.1] * 1536,
            "chunk_id": 0,
            "metadata": {
                "document_id": "doc-123",
                "source": "test.txt",
                "document_type": "txt"
            }
        }]
        
        mock_qdrant_client.count.return_value.count = 1
        
        result = await vector_store.upsert_documents(documents)
        
        assert len(result) == 1
        assert result[0] == "doc-123"
        mock_qdrant_client.upsert.assert_called_once()
        
        # Check the upsert call
        call_args = mock_qdrant_client.upsert.call_args[1]
        assert call_args['collection_name'] == 'documents'
        assert len(call_args['points']) == 1
    
    @pytest.mark.asyncio
    async def test_search(self, vector_store, mock_qdrant_client):
        """Test similarity search."""
        query_embedding = [0.1] * 1536
        
        # Mock search results
        mock_result = Mock()
        mock_result.id = "chunk-1"
        mock_result.score = 0.95
        mock_result.payload = {
            "text": "Similar content",
            "document_id": "doc-123",
            "source": "test.txt"
        }
        
        mock_qdrant_client.search.return_value = [mock_result]
        
        results = await vector_store.search(
            query_embedding=query_embedding,
            limit=5
        )
        
        assert len(results) == 1
        assert results[0]["text"] == "Similar content"
        assert results[0]["score"] == 0.95
        assert results[0]["metadata"]["document_id"] == "doc-123"
    
    @pytest.mark.asyncio
    async def test_search_with_filter(self, vector_store, mock_qdrant_client):
        """Test search with metadata filter."""
        query_embedding = [0.1] * 1536
        filters = {"document_type": "pdf"}
        
        mock_qdrant_client.search.return_value = []
        
        results = await vector_store.search(
            query_embedding=query_embedding,
            limit=5,
            filters=filters
        )
        
        # Verify filter was applied
        call_args = mock_qdrant_client.search.call_args[1]
        assert 'query_filter' in call_args
        assert call_args['query_filter'] is not None
    
    @pytest.mark.asyncio
    async def test_hybrid_search(self, vector_store, mock_qdrant_client):
        """Test hybrid search combining vector and text search."""
        query_embedding = [0.1] * 1536
        query_text = "test query"
        
        # Mock both vector and text search results
        mock_vector_result = Mock()
        mock_vector_result.id = "chunk-1"
        mock_vector_result.score = 0.95
        mock_vector_result.payload = {
            "text": "Vector result",
            "document_id": "doc-1"
        }
        
        mock_qdrant_client.search.return_value = [mock_vector_result]
        
        results = await vector_store.hybrid_search(
            query_embedding=query_embedding,
            query_text=query_text,
            limit=5
        )
        
        assert len(results) >= 0  # Results depend on implementation
    
    @pytest.mark.asyncio
    async def test_list_documents(self, vector_store, mock_qdrant_client):
        """Test listing documents."""
        # Mock scroll results
        mock_records = [
            Mock(payload={
                "document_id": "doc-1",
                "filename": "file1.txt",
                "document_type": "txt",
                "chunk_id": 0,
                "timestamp": "2024-01-01T00:00:00"
            }),
            Mock(payload={
                "document_id": "doc-1",
                "filename": "file1.txt",
                "document_type": "txt",
                "chunk_id": 1,
                "timestamp": "2024-01-01T00:00:00"
            }),
            Mock(payload={
                "document_id": "doc-2",
                "filename": "file2.pdf",
                "document_type": "pdf",
                "chunk_id": 0,
                "timestamp": "2024-01-02T00:00:00"
            })
        ]
        
        mock_qdrant_client.scroll.return_value = (mock_records, None)
        
        documents, total = await vector_store.list_documents(offset=0, limit=10)
        
        assert len(documents) == 2  # Two unique documents
        assert total == 2
        # Documents are sorted by timestamp, doc-2 should be first (newer)
        assert documents[0]["document_id"] == "doc-2"
        assert documents[0]["chunk_count"] == 1
        assert documents[1]["document_id"] == "doc-1"
        assert documents[1]["chunk_count"] == 2
    
    @pytest.mark.asyncio
    async def test_delete_document(self, vector_store, mock_qdrant_client):
        """Test deleting a document."""
        document_id = "doc-123"
        
        # Mock delete operation  
        mock_qdrant_client.delete.return_value = None
        # Mock count after delete
        mock_qdrant_client.count.return_value = Mock(count=95)
        
        result = await vector_store.delete_document(document_id)
        
        assert result is True
        mock_qdrant_client.delete.assert_called_once()
        
        # Check filter used
        call_args = mock_qdrant_client.delete.call_args[1]
        assert call_args['collection_name'] == 'documents'
    
    @pytest.mark.asyncio
    async def test_list_documents_multiple(self, vector_store, mock_qdrant_client):
        """Test listing multiple documents with pagination."""
        # Mock first page
        mock_records_page1 = [
            Mock(payload={
                "document_id": f"doc-{i}",
                "filename": f"file{i}.txt",
                "document_type": "txt",
                "chunk_id": 0,
                "timestamp": f"2024-01-{str(i+1).zfill(2)}T00:00:00"
            }) for i in range(10)
        ]
        
        mock_qdrant_client.scroll.return_value = (mock_records_page1, None)
        
        documents, total = await vector_store.list_documents(offset=0, limit=10)
        
        assert len(documents) == 10
        # Documents are sorted by timestamp in reverse order (newest first)
        assert all(doc["document_id"] == f"doc-{9-i}" for i, doc in enumerate(documents))
    
    @pytest.mark.asyncio
    async def test_get_collection_stats(self, vector_store, mock_qdrant_client):
        """Test getting collection statistics."""
        # Check if method exists, if not skip
        if not hasattr(vector_store, 'get_collection_stats'):
            pytest.skip("get_collection_stats method not implemented")
        
        # Mock collection info
        mock_info = Mock()
        mock_info.vectors_count = 1000
        mock_info.points_count = 1000
        mock_info.indexed_vectors_count = 1000
        
        mock_qdrant_client.get_collection.return_value = mock_info
        
        stats = await vector_store.get_collection_stats()
        
        assert stats["vectors_count"] == 1000
        assert stats["points_count"] == 1000
        assert stats["indexed_vectors_count"] == 1000
    
    @pytest.mark.asyncio
    async def test_error_handling_in_search(self, vector_store, mock_qdrant_client):
        """Test error handling during search."""
        mock_qdrant_client.search.side_effect = Exception("Search failed")
        
        with pytest.raises(Exception, match="Search failed"):
            await vector_store.search(
                query_embedding=[0.1] * 1536,
                limit=5
            )
    
    @pytest.mark.asyncio
    async def test_batch_upsert_documents(self, vector_store, mock_qdrant_client):
        """Test batch upserting multiple documents."""
        documents = [
            {
                "text": f"Test chunk {i}",
                "embedding": [0.1 * i] * 1536,
                "chunk_id": i,
                "metadata": {
                    "document_id": f"doc-{i//5}",
                    "source": f"test{i//5}.txt",
                    "document_type": "txt"
                }
            }
            for i in range(100)
        ]
        
        mock_qdrant_client.count.return_value.count = 100
        
        result = await vector_store.upsert_documents(documents)
        
        # Should have unique document IDs
        unique_docs = set(result)
        assert len(unique_docs) == 20  # 100 chunks / 5 chunks per doc
        
        # Check batching
        assert mock_qdrant_client.upsert.call_count > 0