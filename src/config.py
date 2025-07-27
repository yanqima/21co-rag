from typing import Optional, Dict, Any
from pydantic_settings import BaseSettings
from pydantic import Field, validator
import os


class Settings(BaseSettings):
    # API Configuration
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    api_workers: int = Field(default=4, env="API_WORKERS")
    
    # OpenAI Configuration
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-3.5-turbo", env="OPENAI_MODEL")
    
    # Vector Database Configuration
    qdrant_host: str = Field(default="localhost", env="QDRANT_HOST")
    qdrant_port: int = Field(default=6333, env="QDRANT_PORT")
    qdrant_collection: str = Field(default="documents", env="QDRANT_COLLECTION")
    
    # Redis Configuration
    redis_host: str = Field(default="localhost", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    redis_db: int = Field(default=0, env="REDIS_DB")
    
    # Document Processing Configuration
    chunk_size: int = Field(default=512, env="CHUNK_SIZE")
    chunk_overlap: int = Field(default=50, env="CHUNK_OVERLAP")
    batch_size: int = Field(default=32, env="BATCH_SIZE")
    
    # Embedding Configuration
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2", 
        env="EMBEDDING_MODEL"
    )
    embedding_dimension: int = Field(default=1536, env="EMBEDDING_DIMENSION")  # OpenAI ada-002 dimension
    
    # Search Configuration
    similarity_threshold: float = Field(default=0.7, env="SIMILARITY_THRESHOLD")
    search_limit: int = Field(default=10, env="SEARCH_LIMIT")
    hybrid_search_alpha: float = Field(default=0.5, env="HYBRID_SEARCH_ALPHA")
    
    # Monitoring Configuration
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    
    # Security Configuration
    api_key_header: str = Field(default="X-API-Key", env="API_KEY_HEADER")
    rate_limit_per_minute: int = Field(default=100, env="RATE_LIMIT_PER_MINUTE")
    
    # Environment
    environment: str = Field(default="development", env="ENVIRONMENT")
    
    @validator("similarity_threshold")
    def validate_similarity_threshold(cls, v):
        if not 0 <= v <= 1:
            raise ValueError("Similarity threshold must be between 0 and 1")
        return v
    
    @validator("hybrid_search_alpha")
    def validate_hybrid_search_alpha(cls, v):
        if not 0 <= v <= 1:
            raise ValueError("Hybrid search alpha must be between 0 and 1")
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()