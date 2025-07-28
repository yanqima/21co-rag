"""
Tests for configuration module.
"""
import pytest
import os
from unittest.mock import patch

from src.config import Settings


class TestSettings:
    """Test configuration loading and defaults."""
    
    def test_default_config_values(self):
        """Test that default configuration values are set correctly."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True):
            config = Settings()
            
            # API defaults
            assert config.api_host == "0.0.0.0"
            assert config.api_port == 8000
            assert config.api_workers == 4
            
            # Vector DB defaults
            assert config.qdrant_host == "localhost"
            assert config.qdrant_port == 6333
            assert config.qdrant_collection == "documents"
            
            # Redis defaults
            assert config.redis_host == "localhost"
            assert config.redis_port == 6379
            assert config.redis_db == 0
            
            # Processing defaults
            assert config.chunk_size == 512
            assert config.chunk_overlap == 50
            assert config.batch_size == 32
            
            # Embedding defaults
            assert config.embedding_model == "sentence-transformers/all-MiniLM-L6-v2"
            assert config.embedding_dimension == 384
            
            # Search defaults
            assert config.similarity_threshold == 0.4
            assert config.search_limit == 10
            assert config.hybrid_search_alpha == 0.5
    
    def test_environment_variable_override(self):
        """Test that environment variables override defaults."""
        test_env = {
            "OPENAI_API_KEY": "test-key-123",
            "API_HOST": "127.0.0.1",
            "API_PORT": "9000",
            "QDRANT_HOST": "qdrant.example.com",
            "REDIS_HOST": "redis.example.com",
            "CHUNK_SIZE": "1024"
        }
        
        with patch.dict(os.environ, test_env, clear=True):
            config = Settings()
            
            assert config.api_host == "127.0.0.1"
            assert config.api_port == 9000  # Should be converted to int
            assert config.qdrant_host == "qdrant.example.com"
            assert config.redis_host == "redis.example.com"
            assert config.chunk_size == 1024
            assert config.openai_api_key == "test-key-123"
    
    def test_openai_configuration(self):
        """Test OpenAI configuration."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key", "OPENAI_MODEL": "gpt-4"}, clear=True):
            config = Settings()
            
            assert config.openai_api_key == "test-key"
            assert config.openai_model == "gpt-4"
    
    def test_monitoring_configuration(self):
        """Test monitoring configuration."""
        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "test-key",
            "LOG_LEVEL": "DEBUG",
            "ENABLE_METRICS": "false"
        }, clear=True):
            config = Settings()
            
            assert config.log_level == "DEBUG"
            assert config.enable_metrics is False
    
    def test_rate_limiting_config(self):
        """Test rate limiting configuration."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True):
            config = Settings()
            
            assert config.rate_limit_per_minute == 100
            assert config.api_key_header == "X-API-Key"
    
    def test_missing_required_fields(self):
        """Test that settings work with defaults even without env vars."""
        with patch.dict(os.environ, {}, clear=True):
            # Should work with defaults - only OPENAI_API_KEY might be required
            settings = Settings()
            # All fields should have reasonable defaults
            assert settings.api_port > 0
            assert settings.chunk_size > 0
            assert settings.batch_size > 0
    
    def test_type_conversion(self):
        """Test that string values are converted to correct types."""
        test_env = {
            "OPENAI_API_KEY": "test-key",
            "API_PORT": "8080",
            "QDRANT_PORT": "6334",
            "SIMILARITY_THRESHOLD": "0.75",
            "ENABLE_METRICS": "true"
        }
        
        with patch.dict(os.environ, test_env, clear=True):
            config = Settings()
            
            assert isinstance(config.api_port, int)
            assert config.api_port == 8080
            assert isinstance(config.qdrant_port, int)
            assert config.qdrant_port == 6334
            assert isinstance(config.similarity_threshold, float)
            assert config.similarity_threshold == 0.75
            assert isinstance(config.enable_metrics, bool)
            assert config.enable_metrics is True
    
    def test_file_path_config(self):
        """Test configuration values that represent file paths."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True):
            config = Settings()
            
            # Ensure embedding model path is valid
            assert isinstance(config.embedding_model, str)
            assert len(config.embedding_model) > 0