"""
Tests for the ReAct agent module.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from typing import List, Dict, Any

from src.processing.react_agent import (
    DocumentSearchTool,
    SystemInfoTool,
    LangChainReActAgent
)


class TestDocumentSearchTool:
    """Test DocumentSearchTool class."""
    
    @pytest.fixture
    def mock_search_function(self):
        """Create mock search function."""
        return AsyncMock()
    
    @pytest.fixture
    def search_tool(self, mock_search_function):
        """Create DocumentSearchTool instance."""
        search_params = {
            "query_embedding": [0.1] * 1536,
            "top_k": 5
        }
        return DocumentSearchTool(mock_search_function, search_params)
    
    @pytest.mark.asyncio
    async def test_search_with_results(self, search_tool, mock_search_function):
        """Test search with results."""
        mock_results = [
            {
                "text": "Result 1 text",
                "score": 0.95,
                "metadata": {"filename": "doc1.txt"}
            },
            {
                "text": "Result 2 text",
                "score": 0.85,
                "metadata": {"filename": "doc2.txt"}
            }
        ]
        mock_search_function.return_value = mock_results
        
        result = await search_tool.search("test query")
        
        assert "Found 2 relevant documents" in result
        assert "Result 1 text" in result
        assert "Result 2 text" in result
        assert "doc1.txt" in result
        assert "95.0%" in result  # Score formatting
        assert search_tool.last_search_results == mock_results
    
    @pytest.mark.asyncio
    async def test_search_no_results(self, search_tool, mock_search_function):
        """Test search with no results."""
        mock_search_function.return_value = []
        
        result = await search_tool.search("test query")
        
        assert result == "No relevant documents found for this query."
        assert search_tool.last_search_results == []
    
    @pytest.mark.asyncio
    async def test_search_error_handling(self, search_tool):
        """Test search error handling."""
        # Directly replace the search function to raise a real exception
        async def mock_search_with_error(*args, **kwargs):
            raise Exception("Search error")
        
        search_tool.search_function = mock_search_with_error
        
        # Mock the logger to avoid MagicMock string conversion issue
        with patch('src.processing.react_agent.logger'):
            result = await search_tool.search("test query")
        
        assert "Error searching documents" in result
        assert "Search error" in result
    
    @pytest.mark.asyncio
    async def test_search_limits_results(self, search_tool, mock_search_function):
        """Test that search limits results to top 3."""
        mock_results = [
            {"text": f"Result {i}", "score": 0.9 - i*0.1, "metadata": {"filename": f"doc{i}.txt"}}
            for i in range(10)
        ]
        mock_search_function.return_value = mock_results
        
        result = await search_tool.search("test query")
        
        # Should only show top 3
        assert "Result 0" in result
        assert "Result 1" in result
        assert "Result 2" in result
        assert "Result 3" not in result


class TestSystemInfoTool:
    """Test SystemInfoTool class."""
    
    @pytest.fixture
    def mock_vector_store(self):
        """Create mock vector store."""
        return Mock()
    
    @pytest.fixture
    def system_info_tool(self, mock_vector_store):
        """Create SystemInfoTool instance."""
        return SystemInfoTool(mock_vector_store)
    
    @pytest.mark.asyncio
    async def test_get_document_count(self, system_info_tool, mock_vector_store):
        """Test getting document count."""
        mock_vector_store.list_documents = AsyncMock(return_value=([], 42))
        
        result = await system_info_tool.get_info("how many documents")
        
        assert "42 documents" in result
    
    @pytest.mark.asyncio
    async def test_list_documents(self, system_info_tool, mock_vector_store):
        """Test listing documents."""
        mock_docs = [
            {
                "filename": "doc1.pdf",
                "document_type": "pdf",
                "chunk_count": 10
            },
            {
                "filename": "doc2.txt",
                "document_type": "txt",
                "chunk_count": 5
            }
        ]
        mock_vector_store.list_documents = AsyncMock(return_value=(mock_docs, 2))
        
        result = await system_info_tool.get_info("list all documents")
        
        assert "2 documents" in result
        assert "doc1.pdf" in result
        assert "PDF" in result
        assert "10 chunks" in result
        assert "doc2.txt" in result
    
    @pytest.mark.asyncio
    async def test_no_documents(self, system_info_tool, mock_vector_store):
        """Test when no documents exist."""
        mock_vector_store.list_documents = AsyncMock(return_value=([], 0))
        
        result = await system_info_tool.get_info("list documents")
        
        assert "No documents have been uploaded" in result
    
    @pytest.mark.asyncio
    async def test_error_handling(self, system_info_tool):
        """Test error handling."""
        # Replace the list_documents method to raise a real exception
        async def mock_list_with_error(*args, **kwargs):
            raise Exception("DB error")
        
        system_info_tool.vector_store.list_documents = mock_list_with_error
        
        # Mock the logger to avoid MagicMock string conversion issue
        with patch('src.processing.react_agent.logger'):
            result = await system_info_tool.get_info("how many documents")
        
        assert "Error getting system information" in result


class TestLangChainReActAgent:
    """Test LangChainReActAgent class."""
    
    def test_singleton_pattern(self):
        """Test that agent is a singleton."""
        # Reset the singleton state
        LangChainReActAgent._instance = None
        LangChainReActAgent._initialized = False
        
        agent1 = LangChainReActAgent()
        agent2 = LangChainReActAgent()
        
        assert agent1 is agent2
    
    def test_initialization(self):
        """Test agent initialization."""
        agent = LangChainReActAgent()
        
        assert agent.llm is None  # Not initialized until needed
        assert agent.agent is None
        assert agent.doc_search_tool is None
        assert agent.system_info_tool is None
        assert agent.memory is not None
    
    def test_create_tools(self):
        """Test tool creation."""
        agent = LangChainReActAgent()
        mock_search = AsyncMock()
        mock_vector_store = Mock()
        
        tools = agent._create_tools(mock_search, {}, mock_vector_store)
        
        assert len(tools) == 2
        assert tools[0].name == "search_documents"
        assert tools[1].name == "get_system_info"
        assert agent.doc_search_tool is not None
        assert agent.system_info_tool is not None
    
    @pytest.mark.asyncio
    async def test_process_query_with_search(self):
        """Test processing query that requires search."""
        # Reset singleton to ensure clean state
        LangChainReActAgent._instance = None
        LangChainReActAgent._initialized = False
        
        agent = LangChainReActAgent()
        
        mock_search = AsyncMock(return_value=[
            {"text": "RAG is Retrieval Augmented Generation", "score": 0.95, "metadata": {}}
        ])
        mock_vector_store = Mock()
        
        with patch.object(agent, '_initialize_llm') as mock_init:
            with patch('src.processing.react_agent.initialize_agent') as mock_agent:
                # Mock the agent response
                mock_agent_instance = Mock()
                mock_agent_instance.arun = AsyncMock(
                    return_value="Based on the search results, RAG stands for Retrieval Augmented Generation."
                )
                mock_agent.return_value = mock_agent_instance
                
                result = await agent.process_query(
                    "What is RAG?",
                    mock_search,
                    {},
                    mock_vector_store
                )
                
                assert "answer" in result
                assert "results" in result
                assert "total_results" in result
                assert "agent_action" in result
    
    @pytest.mark.asyncio
    async def test_fallback_processing(self):
        """Test fallback processing when LLM fails."""
        # Reset singleton
        LangChainReActAgent._instance = None
        LangChainReActAgent._initialized = False
        
        with patch('src.processing.react_agent.ChatOpenAI', side_effect=Exception("API error")):
            # Mock the logger to avoid MagicMock string conversion issue
            with patch('src.processing.react_agent.logger'):
                agent = LangChainReActAgent()
                
                mock_search = AsyncMock(return_value=[])
                mock_vector_store = Mock()
                mock_vector_store.list_documents = AsyncMock(return_value=([], 0))
                
                result = await agent.process_query(
                    "Hello",
                    mock_search,
                    {},
                    mock_vector_store
                )
                
                assert "answer" in result
                assert "Hello!" in result["answer"]
                assert result["agent_action"] == "direct_response"
    
    def test_initialize_llm(self):
        """Test LLM initialization."""
        agent = LangChainReActAgent()
        
        with patch('src.processing.react_agent.ChatOpenAI') as mock_openai:
            agent._initialize_llm()
            
            assert agent.llm is not None
            mock_openai.assert_called_once()
    
    def test_initialize_llm_error_handling(self):
        """Test LLM initialization error handling."""
        # Reset singleton to ensure clean state
        LangChainReActAgent._instance = None
        LangChainReActAgent._initialized = False
        
        with patch('src.processing.react_agent.ChatOpenAI', side_effect=Exception("API error")):
            agent = LangChainReActAgent()
            # LLM should be None due to initialization failure
            assert agent.llm is None


class TestAgentIntegration:
    """Test agent integration scenarios."""
    
    @pytest.mark.asyncio
    async def test_full_query_flow(self):
        """Test complete query processing flow."""
        # Reset singleton
        LangChainReActAgent._instance = None
        LangChainReActAgent._initialized = False
        
        agent = LangChainReActAgent()
        
        mock_search = AsyncMock(return_value=[
            {
                "text": "Python is a programming language",
                "score": 0.9,
                "metadata": {"filename": "python_guide.pdf"}
            }
        ])
        mock_vector_store = Mock()
        mock_vector_store.list_documents = AsyncMock(return_value=([], 5))
        
        with patch('src.processing.react_agent.ChatOpenAI'):
            with patch('src.processing.react_agent.initialize_agent') as mock_init:
                mock_agent = Mock()
                mock_agent.arun = AsyncMock(return_value="Python is a high-level programming language.")
                mock_init.return_value = mock_agent
                
                result = await agent.process_query(
                    "What is Python?",
                    mock_search,
                    {},
                    mock_vector_store
                )
                
                assert result["answer"] is not None
                assert isinstance(result["results"], list)
                assert result["total_results"] >= 0
                assert "agent_action" in result