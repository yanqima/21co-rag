from typing import List, Dict, Any, Protocol
from abc import ABC, abstractmethod
import re
from src.config import settings
from src.monitoring.logger import get_logger

logger = get_logger(__name__)


class ChunkingStrategy(ABC):
    """Abstract base class for chunking strategies."""
    
    @abstractmethod
    def chunk(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Split text into chunks with metadata."""
        pass


class FixedSizeChunking(ChunkingStrategy):
    """Fixed-size chunking with overlap."""
    
    def __init__(self, chunk_size: int = None, overlap: int = None):
        self.chunk_size = chunk_size or settings.chunk_size
        self.overlap = overlap or settings.chunk_overlap
    
    def chunk(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Split text into fixed-size chunks with overlap."""
        if not text:
            return []
        
        chunks = []
        text_length = len(text)
        start = 0
        chunk_id = 0
        
        while start < text_length:
            end = min(start + self.chunk_size, text_length)
            chunk_text = text[start:end]
            
            chunk_data = {
                "text": chunk_text,
                "chunk_id": chunk_id,
                "start_index": start,
                "end_index": end,
                "metadata": metadata or {}
            }
            
            chunks.append(chunk_data)
            
            # Move to next chunk with overlap
            start = end - self.overlap if end < text_length else end
            chunk_id += 1
        
        logger.info(
            "fixed_size_chunking_completed",
            chunks_created=len(chunks),
            text_length=text_length,
            chunk_size=self.chunk_size,
            overlap=self.overlap
        )
        
        return chunks


class SemanticChunking(ChunkingStrategy):
    """Semantic chunking based on paragraph/sentence boundaries."""
    
    def __init__(self, max_chunk_size: int = None):
        self.max_chunk_size = max_chunk_size or settings.chunk_size
    
    def chunk(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Split text on semantic boundaries (paragraphs and sentences)."""
        if not text:
            return []
        
        # Split by paragraphs first
        paragraphs = re.split(r'\n\n+', text.strip())
        
        chunks = []
        current_chunk = []
        current_size = 0
        chunk_id = 0
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            
            paragraph_size = len(paragraph)
            
            # If paragraph is too large, split by sentences
            if paragraph_size > self.max_chunk_size:
                sentences = re.split(r'(?<=[.!?])\s+', paragraph)
                
                for sentence in sentences:
                    sentence_size = len(sentence)
                    
                    if current_size + sentence_size > self.max_chunk_size and current_chunk:
                        # Save current chunk
                        chunk_text = ' '.join(current_chunk)
                        chunks.append({
                            "text": chunk_text,
                            "chunk_id": chunk_id,
                            "metadata": metadata or {}
                        })
                        chunk_id += 1
                        current_chunk = [sentence]
                        current_size = sentence_size
                    else:
                        current_chunk.append(sentence)
                        current_size += sentence_size + 1  # +1 for space
            
            # If adding paragraph exceeds limit, save current chunk
            elif current_size + paragraph_size > self.max_chunk_size and current_chunk:
                chunk_text = '\n\n'.join(current_chunk)
                chunks.append({
                    "text": chunk_text,
                    "chunk_id": chunk_id,
                    "metadata": metadata or {}
                })
                chunk_id += 1
                current_chunk = [paragraph]
                current_size = paragraph_size
            else:
                current_chunk.append(paragraph)
                current_size += paragraph_size + 2  # +2 for \n\n
        
        # Don't forget the last chunk
        if current_chunk:
            chunk_text = '\n\n'.join(current_chunk) if len(current_chunk) > 1 else current_chunk[0]
            chunks.append({
                "text": chunk_text,
                "chunk_id": chunk_id,
                "metadata": metadata or {}
            })
        
        logger.info(
            "semantic_chunking_completed",
            chunks_created=len(chunks),
            text_length=len(text),
            max_chunk_size=self.max_chunk_size
        )
        
        return chunks


class SlidingWindowChunking(ChunkingStrategy):
    """Sliding window chunking with configurable window and stride."""
    
    def __init__(self, window_size: int = None, stride: int = None):
        self.window_size = window_size or settings.chunk_size
        self.stride = stride or (self.window_size // 2)  # Default 50% overlap
    
    def chunk(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Split text using sliding window approach."""
        if not text:
            return []
        
        chunks = []
        text_length = len(text)
        start = 0
        chunk_id = 0
        
        while start < text_length:
            end = min(start + self.window_size, text_length)
            chunk_text = text[start:end]
            
            chunk_data = {
                "text": chunk_text,
                "chunk_id": chunk_id,
                "start_index": start,
                "end_index": end,
                "metadata": metadata or {}
            }
            
            chunks.append(chunk_data)
            
            # Move window by stride
            start += self.stride
            chunk_id += 1
            
            # Break if remaining text is less than stride
            if start + self.stride >= text_length and start < text_length:
                # Add final chunk with remaining text
                chunk_data = {
                    "text": text[start:],
                    "chunk_id": chunk_id,
                    "start_index": start,
                    "end_index": text_length,
                    "metadata": metadata or {}
                }
                chunks.append(chunk_data)
                break
        
        logger.info(
            "sliding_window_chunking_completed",
            chunks_created=len(chunks),
            text_length=text_length,
            window_size=self.window_size,
            stride=self.stride
        )
        
        return chunks


class ChunkingFactory:
    """Factory for creating chunking strategies."""
    
    @staticmethod
    def create_strategy(strategy_type: str, **kwargs) -> ChunkingStrategy:
        """Create a chunking strategy based on type."""
        strategies = {
            "fixed": FixedSizeChunking,
            "semantic": SemanticChunking,
            "sliding_window": SlidingWindowChunking
        }
        
        strategy_class = strategies.get(strategy_type.lower())
        if not strategy_class:
            raise ValueError(f"Unknown chunking strategy: {strategy_type}")
        
        return strategy_class(**kwargs)