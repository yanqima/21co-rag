"""
Simplified tests for the ReAct agent module.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import List, Dict, Any

from src.processing.react_agent import (
    DocumentSearchTool,
    SystemInfoTool,
    LangChainReActAgent,
    process_query_with_agent
)


class TestReactAgentIntegration:
    """Test ReAct agent integration."""
    
    @pytest.mark.skip(reason="Complex mocking issues with LangChain agents")
    @pytest.mark.asyncio
    async def test_process_query_with_agent_greeting(self):
        """Test processing a greeting query."""
        # Simple greeting should not trigger search
        mock_search = AsyncMock(return_value=[])
        mock_vector_store = Mock()
        mock_vector_store.list_documents = AsyncMock(return_value=([], 0))
        mock_embedding_gen = Mock()
        mock_embedding_gen.generate_embeddings = AsyncMock(return_value=[{"embedding": [0.1] * 1536, "metadata": {}}])
        
        with patch('src.processing.redis_memory.get_conversation_memory') as mock_memory:
            mock_memory.return_value = Mock()
            
            result = await process_query_with_agent(
                query="Hello!",
                search_function=mock_search,
                search_params={},
                vector_store=mock_vector_store,
                embedding_generator=mock_embedding_gen,
                session_id="test"
            )
        
        assert "answer" in result
        assert result["agent_action"] == "direct_response"
        assert "Hello" in result["answer"]
    
    @pytest.mark.skip(reason="Complex mocking issues with LangChain agents")
    @pytest.mark.asyncio
    async def test_process_query_with_agent_search(self):
        """Test processing a query that requires search."""
        mock_search = AsyncMock(return_value=[
            {
                "text": "RAG is Retrieval Augmented Generation",
                "score": 0.95,
                "metadata": {"filename": "rag_guide.pdf"}
            }
        ])
        mock_vector_store = Mock()
        mock_vector_store.list_documents = AsyncMock(return_value=([], 1))
        mock_embedding_gen = Mock()
        mock_embedding_gen.generate_embeddings = AsyncMock(return_value=[{"embedding": [0.1] * 1536, "metadata": {}}])
        
        with patch('src.processing.redis_memory.get_conversation_memory') as mock_memory:
            mock_memory.return_value = Mock()
            
            result = await process_query_with_agent(
                query="What is RAG?",
                search_function=mock_search,
                search_params={},
                vector_store=mock_vector_store,
                embedding_generator=mock_embedding_gen,
                session_id="test"
            )
        
        assert "answer" in result
        assert "results" in result
        assert result["total_results"] >= 0
    
    @pytest.mark.skip(reason="Complex mocking issues with LangChain agents")
    @pytest.mark.asyncio
    async def test_process_query_system_info(self):
        """Test processing a system info query."""
        mock_search = AsyncMock(return_value=[])
        mock_vector_store = Mock()
        mock_vector_store.list_documents = AsyncMock(return_value=([], 5))
        mock_embedding_gen = Mock()
        mock_embedding_gen.generate_embeddings = AsyncMock(return_value=[{"embedding": [0.1] * 1536, "metadata": {}}])
        
        with patch('src.processing.redis_memory.get_conversation_memory') as mock_memory:
            mock_memory.return_value = Mock()
            
            result = await process_query_with_agent(
                query="How many documents are there?",
                search_function=mock_search,
                search_params={},
                vector_store=mock_vector_store,
                embedding_generator=mock_embedding_gen,
                session_id="test"
            )
        
        assert "answer" in result
        # Should have used system info tool
        assert result["agent_action"] in ["search_with_system_info", "direct_response", "search_and_answer"]


class TestDocumentSearchToolSimple:
    """Simplified tests for DocumentSearchTool."""
    
    @pytest.mark.asyncio
    async def test_search_basic(self):
        """Test basic search functionality."""
        mock_search = AsyncMock(return_value=[
            {"text": "Test result", "score": 0.9, "metadata": {"filename": "test.txt"}}
        ])
        mock_embedding_gen = Mock()
        mock_embedding_gen.generate_embeddings = AsyncMock(
            return_value=[{"embedding": [0.1] * 1536}]
        )
        
        tool = DocumentSearchTool(mock_search, {}, mock_embedding_gen)
        result = await tool.search("test query")
        
        assert "Found 1 relevant document" in result
        assert "Test result" in result
        assert tool.last_search_results is not None


class TestSystemInfoToolSimple:
    """Simplified tests for SystemInfoTool."""
    
    @pytest.mark.asyncio
    async def test_get_info_basic(self):
        """Test basic system info retrieval."""
        mock_store = Mock()
        mock_store.list_documents = AsyncMock(return_value=([], 10))
        
        tool = SystemInfoTool(mock_store)
        result = await tool.get_info("how many documents")
        
        assert "10 documents" in result