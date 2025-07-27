from typing import List, Dict, Any, Protocol
from abc import ABC, abstractmethod
from langchain.text_splitter import (
    CharacterTextSplitter,
    RecursiveCharacterTextSplitter
)
from langchain_experimental.text_splitter import SemanticChunker
from langchain_openai import OpenAIEmbeddings
from src.config import settings
from src.monitoring.logger import get_logger

logger = get_logger(__name__)


class ChunkingStrategy(ABC):
    """Abstract base class for chunking strategies."""
    
    @abstractmethod
    def chunk(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Split text into chunks with metadata."""
        pass


class SlidingWindowChunking(ChunkingStrategy):
    """Sliding window chunking with overlap using CharacterTextSplitter."""
    
    def __init__(self, chunk_size: int = None, chunk_overlap: int = None):
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap
        
        # Use CharacterTextSplitter for sliding window with overlap
        self.splitter = CharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap
        )
    
    def chunk(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Split text into sliding window chunks with overlap."""
        if not text:
            return []
        
        # Get chunks from LangChain
        chunk_texts = self.splitter.split_text(text)
        
        # Format chunks with metadata
        chunks = []
        for chunk_id, chunk_text in enumerate(chunk_texts):
            chunk_data = {
                "text": chunk_text,
                "chunk_id": chunk_id,
                "metadata": {
                    **(metadata or {}),
                    "chunk_id": chunk_id,
                    "chunking_strategy": "sliding_window"
                }
            }
            chunks.append(chunk_data)
        
        logger.info(
            "sliding_window_chunking_completed",
            chunks_created=len(chunks),
            text_length=len(text),
            chunk_size=self.chunk_size,
            overlap=self.chunk_overlap
        )
        
        return chunks


class SentenceParagraphChunking(ChunkingStrategy):
    """Sentence/Paragraph chunking using RecursiveCharacterTextSplitter."""
    
    def __init__(self, max_chunk_size: int = None):
        self.max_chunk_size = max_chunk_size or settings.chunk_size
        
        # Use RecursiveCharacterTextSplitter for sentence/paragraph boundaries
        # Prioritizes paragraph breaks, then sentences
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.max_chunk_size,
            chunk_overlap=0,  # No overlap for clean sentence boundaries
            separators=["\n\n", "\n", ". ", "! ", "? ", " "],
            keep_separator=True
        )
    
    def chunk(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Split text on sentence and paragraph boundaries."""
        if not text:
            return []
        
        # Get chunks from LangChain
        chunk_texts = self.splitter.split_text(text)
        
        # Format chunks with metadata
        chunks = []
        for chunk_id, chunk_text in enumerate(chunk_texts):
            chunk_data = {
                "text": chunk_text,
                "chunk_id": chunk_id,
                "metadata": {
                    **(metadata or {}),
                    "chunk_id": chunk_id,
                    "chunking_strategy": "sentence_paragraph"
                }
            }
            chunks.append(chunk_data)
        
        logger.info(
            "sentence_paragraph_chunking_completed",
            chunks_created=len(chunks),
            text_length=len(text),
            max_chunk_size=self.max_chunk_size
        )
        
        return chunks


class SemanticChunking(ChunkingStrategy):
    """Semantic chunking using SemanticChunker from langchain_experimental."""
    
    def __init__(self):
        # Use OpenAI embeddings for semantic similarity
        embeddings = OpenAIEmbeddings()
        self.splitter = SemanticChunker(embeddings)
    
    def chunk(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Split text based on semantic similarity."""
        if not text:
            return []
        
        # Get chunks from SemanticChunker
        chunk_texts = self.splitter.split_text(text)
        
        # Format chunks with metadata
        chunks = []
        for chunk_id, chunk_text in enumerate(chunk_texts):
            chunk_data = {
                "text": chunk_text,
                "chunk_id": chunk_id,
                "metadata": {
                    **(metadata or {}),
                    "chunk_id": chunk_id,
                    "chunking_strategy": "semantic"
                }
            }
            chunks.append(chunk_data)
        
        logger.info(
            "semantic_chunking_completed",
            chunks_created=len(chunks),
            text_length=len(text)
        )
        
        return chunks


class ChunkingFactory:
    """Factory for creating chunking strategies."""
    
    @staticmethod
    def create_strategy(strategy_type: str, **kwargs) -> ChunkingStrategy:
        """Create a chunking strategy based on type."""
        strategies = {
            "sliding_window": SlidingWindowChunking,
            "sentence_paragraph": SentenceParagraphChunking,
            "semantic": SemanticChunking,
            # Aliases for backward compatibility
            "sliding": SlidingWindowChunking,
            "sentence": SentenceParagraphChunking,
            "paragraph": SentenceParagraphChunking
        }
        
        strategy_class = strategies.get(strategy_type.lower())
        if not strategy_class:
            raise ValueError(f"Unknown chunking strategy: {strategy_type}")
        
        return strategy_class(**kwargs)