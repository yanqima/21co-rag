"""
Redis-based persistent conversation memory for LangChain agents.

This module provides a Redis-backed conversation memory implementation
that persists chat history across stateless API requests using LangChain's
official RedisChatMessageHistory with fallback to custom implementation.
"""

import json
import os
from typing import List, Optional

import redis
from langchain.memory import ConversationBufferMemory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain.memory.chat_message_histories import ChatMessageHistory
from langchain.schema import BaseMessage, HumanMessage, AIMessage

from src.monitoring.logger import get_logger

logger = get_logger(__name__)

# Try to import langchain-redis, fallback to custom implementation
try:
    from langchain_redis import RedisChatMessageHistory
    REDIS_LANGCHAIN_AVAILABLE = True
    logger.info("Using LangChain's official RedisChatMessageHistory")
except ImportError as e:
    REDIS_LANGCHAIN_AVAILABLE = False
    logger.warning(f"langchain-redis not available: {e}. Using custom Redis implementation")


class RedisBackedChatHistory(BaseChatMessageHistory):
    """A simple Redis-backed chat message history."""
    
    def __init__(self, session_id: str, redis_client: Optional[redis.Redis] = None):
        self.session_id = session_id
        self.redis_client = redis_client or self._get_redis_client()
        self.key = f"chat_history:{session_id}"
        
    def _get_redis_client(self) -> Optional[redis.Redis]:
        """Get Redis client."""
        try:
            redis_host = os.getenv('REDIS_HOST', 'localhost')
            redis_port = int(os.getenv('REDIS_PORT', 6379))
            redis_db = int(os.getenv('REDIS_DB', 0))
            
            client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            
            # Test connection
            client.ping()
            return client
            
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}")
            return None
    
    def _serialize_message(self, message: BaseMessage) -> str:
        """Serialize a message to JSON."""
        return json.dumps({
            "type": message.__class__.__name__,
            "content": message.content
        })
    
    def _deserialize_message(self, data: str) -> BaseMessage:
        """Deserialize a message from JSON."""
        try:
            msg_data = json.loads(data)
            msg_type = msg_data["type"]
            content = msg_data["content"]
            
            if msg_type == "HumanMessage":
                return HumanMessage(content=content)
            elif msg_type == "AIMessage":
                return AIMessage(content=content)
            else:
                return HumanMessage(content=content)
        except (json.JSONDecodeError, KeyError):
            return HumanMessage(content=data)
    
    @property
    def messages(self) -> List[BaseMessage]:
        """Get all messages from Redis."""
        if not self.redis_client:
            return []
        
        try:
            message_strings = self.redis_client.lrange(self.key, 0, -1)
            return [self._deserialize_message(msg) for msg in message_strings]
        except Exception as e:
            logger.error(f"Failed to retrieve messages: {e}")
            return []
    
    def add_message(self, message: BaseMessage) -> None:
        """Add a message to Redis."""
        if not self.redis_client:
            return
        
        try:
            serialized = self._serialize_message(message)
            self.redis_client.rpush(self.key, serialized)
            
            # Keep only last 50 messages
            self.redis_client.ltrim(self.key, -50, -1)
            
            # Set expiration (24 hours)
            self.redis_client.expire(self.key, 86400)
            
        except Exception as e:
            logger.error(f"Failed to add message: {e}")
    
    def clear(self) -> None:
        """Clear all messages."""
        if not self.redis_client:
            return
        
        try:
            self.redis_client.delete(self.key)
        except Exception as e:
            logger.error(f"Failed to clear messages: {e}")


def get_redis_history(session_id: str) -> BaseChatMessageHistory:
    """Get or create a Redis-backed chat message history."""
    if REDIS_LANGCHAIN_AVAILABLE:
        try:
            # Use LangChain's official Redis integration
            redis_url = _get_redis_url()
            history = RedisChatMessageHistory(
                session_id=session_id,
                url=redis_url,
                ttl=86400  # 24 hours expiration
            )
            logger.debug(f"Created LangChain Redis chat history for session {session_id}")
            return history
        except Exception as e:
            logger.error(f"Failed to create LangChain Redis chat history: {e}")
            logger.warning("Falling back to custom Redis implementation")
    
    # Fallback to custom Redis implementation
    try:
        return RedisBackedChatHistory(session_id)
    except Exception as e:
        logger.error(f"Failed to create custom Redis chat history: {e}")
        logger.warning("Falling back to in-memory chat history")
        return ChatMessageHistory()


def _get_redis_url() -> str:
    """Get Redis URL from environment variables."""
    redis_host = os.getenv('REDIS_HOST', 'localhost')
    redis_port = os.getenv('REDIS_PORT', '6379')
    redis_db = os.getenv('REDIS_DB', '0')
    
    return f"redis://{redis_host}:{redis_port}/{redis_db}"


def get_conversation_memory(session_id: str, memory_key: str = "chat_history", 
                           return_messages: bool = True) -> ConversationBufferMemory:
    """Get a ConversationBufferMemory instance with Redis-backed chat history."""
    try:
        # Get Redis-backed chat history
        chat_history = get_redis_history(session_id)
        
        # Create ConversationBufferMemory with Redis chat history
        memory = ConversationBufferMemory(
            memory_key=memory_key,
            return_messages=return_messages,
            chat_memory=chat_history
        )
        
        logger.debug(f"Created conversation memory for session {session_id} with {len(chat_history.messages)} existing messages")
        return memory
        
    except Exception as e:
        logger.error(f"Failed to create conversation memory: {e}")
        # Fallback to standard in-memory ConversationBufferMemory
        logger.warning("Falling back to in-memory conversation memory")
        return ConversationBufferMemory(
            memory_key=memory_key,
            return_messages=return_messages
        )
