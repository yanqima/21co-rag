"""
Tests for the custom LLM module.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
import json

from src.processing.custom_llm import CustomOpenAILLM
from src.config import settings


class TestCustomOpenAILLM:
    """Test CustomOpenAILLM class."""
    
    @pytest.fixture
    def mock_httpx(self):
        """Mock httpx for API calls."""
        with patch('httpx.AsyncClient') as mock_class:
            mock_instance = Mock()
            mock_class.return_value.__aenter__.return_value = mock_instance
            mock_class.return_value.__aexit__.return_value = None
            
            # Default successful response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [{
                    "message": {"content": "Test response"}
                }]
            }
            mock_instance.post = AsyncMock(return_value=mock_response)
            
            yield mock_instance
    
    @pytest.fixture
    def llm(self, mock_httpx):
        """Create CustomOpenAILLM instance."""
        with patch('src.processing.custom_llm.settings') as mock_settings:
            mock_settings.openai_api_key = "test-key"
            mock_settings.openai_model = "gpt-3.5-turbo"
            return CustomOpenAILLM()
    
    def test_initialization(self, llm):
        """Test LLM initialization."""
        assert llm.model_name == "gpt-3.5-turbo"
        assert llm.temperature == 0.7
        assert llm.max_tokens == 1000
    
    @pytest.mark.asyncio
    async def test_agenerate_success(self, llm, mock_httpx):
        """Test successful generation."""
        prompts = ["Test prompt"]
        
        result = await llm._agenerate(prompts)
        
        assert result.generations[0][0].text == "Test response"
        mock_httpx.post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_agenerate_with_stop_words(self, llm, mock_httpx):
        """Test generation with stop words."""
        prompts = ["Test prompt"]
        stop = ["STOP", "END"]
        
        result = await llm._agenerate(prompts, stop=stop)
        
        assert result.generations[0][0].text == "Test response"
        # Check that stop words were passed
        call_args = mock_httpx.post.call_args
        assert call_args[1]["json"]["stop"] == stop
    
    @pytest.mark.asyncio
    async def test_agenerate_api_error(self, llm):
        """Test handling API errors."""
        with patch('httpx.AsyncClient') as mock_class:
            mock_instance = Mock()
            mock_class.return_value.__aenter__.return_value = mock_instance
            mock_class.return_value.__aexit__.return_value = None
            
            # Mock error response
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            mock_instance.post = AsyncMock(return_value=mock_response)
            
            prompts = ["Test prompt"]
            
            with pytest.raises(Exception):
                await llm._agenerate(prompts)
    
    @pytest.mark.asyncio
    async def test_agenerate_network_error(self, llm, mock_httpx):
        """Test handling network errors."""
        mock_httpx.post.side_effect = Exception("Network error")
        
        prompts = ["Test prompt"]
        
        with pytest.raises(Exception, match="Network error"):
            await llm._agenerate(prompts)
    
    def test_generate_sync(self, llm, mock_httpx):
        """Test sync generate method."""
        # The sync _generate method calls the async one
        result = llm._generate(["Test prompt"])
        
        assert len(result.generations) == 1
        assert result.generations[0][0].text == "Test response"
    
    def test_llm_type_property(self, llm):
        """Test llm_type property."""
        assert llm._llm_type == "custom_openai"
    
    @pytest.mark.asyncio
    async def test_ainvoke(self, llm, mock_httpx):
        """Test ainvoke method."""
        result = await llm.ainvoke("Test prompt")
        
        # ainvoke returns a string from the LLM, not an object with content
        assert result == "Test response"
        mock_httpx.post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_agenerate_with_run_manager(self, llm, mock_httpx):
        """Test generation with run manager."""
        prompts = ["Test prompt"]
        run_manager = Mock()
        
        result = await llm._agenerate(prompts, run_manager=run_manager)
        
        assert result.generations[0][0].text == "Test response"
    
    def test_temperature_validation(self):
        """Test temperature parameter validation."""
        with patch('src.processing.custom_llm.settings') as mock_settings:
            mock_settings.openai_api_key = "test-key"
            mock_settings.openai_model = "gpt-3.5-turbo"
            
            llm = CustomOpenAILLM(temperature=0.0)
            assert llm.temperature == 0.0
            
            llm = CustomOpenAILLM(temperature=1.0)
            assert llm.temperature == 1.0