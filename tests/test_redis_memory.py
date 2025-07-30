"""
Tests for Redis memory module.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import json
from datetime import datetime

from src.processing.redis_memory import (
    get_conversation_memory,
    RedisBackedChatHistory,
    get_redis_history
)


class TestRedisMemory:
    """Test Redis memory functionality."""
    
    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client."""
        with patch('redis.Redis') as mock_class:
            mock_client = Mock()
            mock_class.return_value = mock_client
            
            # Mock basic Redis operations
            mock_client.lrange.return_value = []
            mock_client.lpush.return_value = 1
            mock_client.delete.return_value = 1
            mock_client.exists.return_value = 0
            mock_client.expire.return_value = True
            
            yield mock_client
    
    @pytest.fixture
    def mock_env(self):
        """Mock environment variables."""
        with patch.dict('os.environ', {
            'REDIS_HOST': 'localhost',
            'REDIS_PORT': '6379',
            'REDIS_DB': '0'
        }):
            yield
    
    def test_get_conversation_memory_success(self, mock_redis, mock_env):
        """Test successful memory retrieval."""
        with patch('src.processing.redis_memory.logger'):
            memory = get_conversation_memory("test-session")
            
            assert memory is not None
            # Should be ConversationBufferMemory instance
            assert hasattr(memory, 'chat_memory')
    
    def test_get_conversation_memory_redis_error(self, mock_env):
        """Test fallback when Redis fails."""
        with patch('redis.Redis', side_effect=Exception("Redis connection failed")):
            with patch('src.processing.redis_memory.logger'):
                memory = get_conversation_memory("test-session")
                
                assert memory is not None
                # Should still return a working memory
    


class TestRedisBackedChatHistory:
    """Test RedisBackedChatHistory class."""
    
    @pytest.fixture
    def mock_redis_history(self):
        """Mock RedisChatMessageHistory."""
        with patch('langchain_redis.RedisChatMessageHistory') as mock_class:
            mock_instance = Mock()
            mock_class.return_value = mock_instance
            
            # Mock messages property
            mock_instance.messages = []
            mock_instance.add_message = Mock()
            mock_instance.clear = Mock()
            
            yield mock_instance
    
    def test_initialization_success(self):
        """Test successful initialization."""
        with patch('redis.Redis') as mock_redis:
            mock_client = Mock()
            mock_redis.return_value = mock_client
            mock_client.ping.return_value = True
            
            history = RedisBackedChatHistory(session_id="test-session")
            
            assert history.session_id == "test-session"
            assert history.key == "chat_history:test-session"
    
    def test_initialization_redis_failure(self):
        """Test initialization when Redis connection fails."""
        with patch('redis.Redis', side_effect=Exception("Connection failed")):
            with patch('src.processing.redis_memory.logger'):
                history = RedisBackedChatHistory(session_id="test-session")
                
                assert history.session_id == "test-session"
                assert history.redis_client is None
    
    def test_add_message_success(self):
        """Test adding message successfully."""
        with patch('redis.Redis') as mock_redis:
            mock_client = Mock()
            mock_redis.return_value = mock_client
            mock_client.ping.return_value = True
            mock_client.rpush.return_value = 1
            mock_client.ltrim.return_value = True
            mock_client.expire.return_value = True
            
            history = RedisBackedChatHistory(session_id="test-session")
            
            from langchain.schema import HumanMessage
            message = HumanMessage(content="Test message")
            
            history.add_message(message)
            
            mock_client.rpush.assert_called_once()
            mock_client.ltrim.assert_called_once_with("chat_history:test-session", -50, -1)
            mock_client.expire.assert_called_once_with("chat_history:test-session", 86400)
    
    def test_add_message_no_redis(self):
        """Test adding message when Redis is not available."""
        history = RedisBackedChatHistory(session_id="test-session")
        history.redis_client = None
        
        from langchain.schema import HumanMessage
        message = HumanMessage(content="Test message")
        
        # Should not raise error
        history.add_message(message)
    
    def test_messages_property(self):
        """Test messages property."""
        with patch('redis.Redis') as mock_redis:
            mock_client = Mock()
            mock_redis.return_value = mock_client
            mock_client.ping.return_value = True
            
            # Mock serialized messages
            mock_client.lrange.return_value = [
                '{"type": "HumanMessage", "content": "Hello"}',
                '{"type": "AIMessage", "content": "Hi there!"}'
            ]
            
            history = RedisBackedChatHistory(session_id="test-session")
            messages = history.messages
            
            assert len(messages) == 2
            assert messages[0].content == "Hello"
            assert messages[1].content == "Hi there!"
    
    def test_clear_success(self):
        """Test clearing messages successfully."""
        with patch('redis.Redis') as mock_redis:
            mock_client = Mock()
            mock_redis.return_value = mock_client
            mock_client.ping.return_value = True
            mock_client.delete.return_value = 1
            
            history = RedisBackedChatHistory(session_id="test-session")
            history.clear()
            
            mock_client.delete.assert_called_once_with("chat_history:test-session")
    
    def test_get_redis_history_langchain_available(self):
        """Test get_redis_history when langchain-redis is available."""
        with patch('src.processing.redis_memory.REDIS_LANGCHAIN_AVAILABLE', True):
            with patch('src.processing.redis_memory.RedisChatMessageHistory') as mock_redis_hist:
                mock_instance = Mock()
                mock_redis_hist.return_value = mock_instance
                
                history = get_redis_history("test-session")
                
                assert history == mock_instance
                mock_redis_hist.assert_called_once()
    
    def test_get_redis_history_fallback(self):
        """Test get_redis_history fallback."""
        with patch('src.processing.redis_memory.REDIS_LANGCHAIN_AVAILABLE', False):
            with patch('redis.Redis') as mock_redis:
                mock_client = Mock()
                mock_redis.return_value = mock_client
                mock_client.ping.return_value = True
                
                history = get_redis_history("test-session")
                
                assert isinstance(history, RedisBackedChatHistory)