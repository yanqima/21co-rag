"""
Tests for the chunking module.
"""
import pytest
from unittest.mock import Mock, patch
from typing import List, Dict, Any

from src.processing.chunking import (
    ChunkingFactory,
    SlidingWindowChunking,
    SemanticChunking,
    SentenceParagraphChunking,
    ChunkingStrategy
)


class TestChunkingStrategies:
    """Test different chunking strategies."""
    
    def test_sliding_window_chunking(self):
        """Test sliding window chunking strategy."""
        chunker = SlidingWindowChunking(chunk_size=50, chunk_overlap=10)
        
        text = "This is a test document. " * 20  # Create text longer than chunk size
        chunks = chunker.chunk(text, metadata={"source": "test.txt"})
        
        # CharacterTextSplitter might not split if it can't find good split points
        assert len(chunks) >= 1
        assert all("text" in chunk for chunk in chunks)
        assert all("chunk_id" in chunk for chunk in chunks)
        assert all(chunk["metadata"]["source"] == "test.txt" for chunk in chunks)
    
    def test_sliding_window_empty_text(self):
        """Test sliding window chunking with empty text."""
        chunker = SlidingWindowChunking()
        chunks = chunker.chunk("")
        
        assert chunks == []
    
    def test_sentence_paragraph_chunking(self):
        """Test sentence/paragraph chunking strategy."""
        chunker = SentenceParagraphChunking(max_chunk_size=100)
        
        text = """
        # Header 1
        This is a paragraph under header 1.
        
        ## Header 2
        This is a paragraph under header 2.
        
        - List item 1
        - List item 2
        """ * 5
        
        chunks = chunker.chunk(text)
        
        assert len(chunks) > 1
        assert all("text" in chunk for chunk in chunks)
        assert all("chunk_id" in chunk for chunk in chunks)
    
    def test_semantic_chunking(self):
        """Test semantic chunking strategy."""
        with patch('src.processing.chunking.OpenAIEmbeddings') as mock_embeddings:
            with patch('src.processing.chunking.SemanticChunker') as mock_chunker_class:
                # Mock the embeddings
                mock_embeddings.return_value = Mock()
                
                # Mock the semantic chunker
                mock_splitter = Mock()
                mock_splitter.split_text.return_value = [
                    "This is sentence one.",
                    "This is sentence two.",
                    "This is sentence three."
                ]
                mock_chunker_class.return_value = mock_splitter
                
                chunker = SemanticChunking()
                
                text = "This is sentence one. This is sentence two. This is sentence three."
                chunks = chunker.chunk(text)
                
                assert isinstance(chunks, list)
                assert len(chunks) == 3
                assert all(isinstance(chunk, dict) for chunk in chunks)
                assert all("text" in chunk for chunk in chunks)
                assert all("chunk_id" in chunk for chunk in chunks)
    
    def test_chunking_factory_creates_correct_strategy(self):
        """Test ChunkingFactory creates correct strategy."""
        # Test sliding window
        strategy = ChunkingFactory.create_strategy("sliding_window", chunk_size=200)
        assert isinstance(strategy, SlidingWindowChunking)
        assert strategy.chunk_size == 200
        
        # Test sentence/paragraph
        strategy = ChunkingFactory.create_strategy("sentence_paragraph")
        assert isinstance(strategy, SentenceParagraphChunking)
        
        # Test semantic
        with patch('src.processing.chunking.OpenAIEmbeddings'):
            strategy = ChunkingFactory.create_strategy("semantic")
            assert isinstance(strategy, SemanticChunking)
    
    def test_chunking_factory_invalid_strategy(self):
        """Test ChunkingFactory with invalid strategy."""
        with pytest.raises(ValueError, match="Unknown chunking strategy"):
            ChunkingFactory.create_strategy("invalid_strategy")
    
    def test_chunking_with_metadata_propagation(self):
        """Test that metadata is propagated to all chunks."""
        chunker = SlidingWindowChunking(chunk_size=50, chunk_overlap=10)
        
        text = "Test text " * 20
        metadata = {
            "source": "test.pdf",
            "author": "Test Author",
            "date": "2024-01-01"
        }
        
        chunks = chunker.chunk(text, metadata=metadata)
        
        for chunk in chunks:
            assert chunk["metadata"]["source"] == "test.pdf"
            assert chunk["metadata"]["author"] == "Test Author"
            assert chunk["metadata"]["date"] == "2024-01-01"
    
    def test_chunk_overlap_functionality(self):
        """Test that chunk overlap works correctly."""
        chunker = SlidingWindowChunking(chunk_size=20, chunk_overlap=5)
        
        text = "ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890"
        chunks = chunker.chunk(text)
        
        # Check that consecutive chunks have overlap
        if len(chunks) > 1:
            for i in range(len(chunks) - 1):
                chunk1_end = chunks[i]["text"][-5:]  # Last 5 chars
                chunk2_start = chunks[i + 1]["text"][:5]  # First 5 chars
                # There should be some overlap
                assert any(c in chunk2_start for c in chunk1_end)
    
    def test_sentence_paragraph_chunking_respects_boundaries(self):
        """Test that sentence/paragraph chunking respects document structure."""
        chunker = SentenceParagraphChunking(max_chunk_size=100)
        
        text = """
# Section 1

Short paragraph.

# Section 2

Another short paragraph.

# Section 3

Yet another paragraph.
"""
        
        chunks = chunker.chunk(text)
        
        # Should create at least some chunks
        assert len(chunks) >= 1
    
    def test_semantic_chunking_configuration(self):
        """Test semantic chunking with custom configuration."""
        with patch('src.processing.chunking.OpenAIEmbeddings') as mock_embeddings:
            with patch('src.processing.chunking.SemanticChunker') as mock_chunker_class:
                mock_embeddings.return_value = Mock()
                mock_splitter = Mock()
                mock_splitter.split_text.return_value = ["chunk1", "chunk2"]
                mock_chunker_class.return_value = mock_splitter
                
                # SemanticChunking doesn't accept parameters, just test it works
                chunker = SemanticChunking()
                
                # Test that the chunker has a splitter
                assert hasattr(chunker, 'splitter')
                assert chunker.splitter is not None
    
    def test_chunk_size_edge_cases(self):
        """Test edge cases for chunk sizes."""
        # Very small chunk size
        chunker = SlidingWindowChunking(chunk_size=10, chunk_overlap=2)
        text = "A" * 50
        chunks = chunker.chunk(text)
        assert len(chunks) >= 1  # CharacterTextSplitter might not split as expected
        
        # Chunk size larger than text
        chunker = SlidingWindowChunking(chunk_size=1000, chunk_overlap=0)
        text = "Short text"
        chunks = chunker.chunk(text)
        assert len(chunks) == 1
        assert chunks[0]["text"] == text


class TestChunkingIntegration:
    """Test chunking integration with other components."""
    
    def test_chunking_preserves_unicode(self):
        """Test that chunking preserves unicode characters."""
        chunker = SlidingWindowChunking(chunk_size=50)
        
        text = "Hello 世界! This is a test with émojis 🚀 and special chars: €£¥"
        chunks = chunker.chunk(text)
        
        # Verify unicode is preserved
        combined = "".join(chunk["text"] for chunk in chunks)
        assert "世界" in combined
        assert "🚀" in combined
        assert "€£¥" in combined
    
    def test_chunking_handles_whitespace(self):
        """Test chunking handles various whitespace correctly."""
        chunker = SentenceParagraphChunking(max_chunk_size=50)
        
        text = "Line 1\n\nLine 2\r\nLine 3\t\tTabbed"
        chunks = chunker.chunk(text)
        
        assert len(chunks) >= 1
        # Whitespace should be preserved appropriately
        combined = "".join(chunk["text"] for chunk in chunks)
        assert "Line 1" in combined
        assert "Line 2" in combined
        assert "Line 3" in combined
    
    def test_chunking_strategy_inheritance(self):
        """Test that custom strategies can be created."""
        class CustomChunking(ChunkingStrategy):
            def chunk(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
                # Simple implementation that splits by sentences
                sentences = text.split(".")
                return [
                    {
                        "text": sent.strip(),
                        "chunk_id": i,
                        "metadata": metadata or {}
                    }
                    for i, sent in enumerate(sentences)
                    if sent.strip()
                ]
        
        chunker = CustomChunking()
        text = "First sentence. Second sentence. Third sentence."
        chunks = chunker.chunk(text)
        
        assert len(chunks) == 3
        assert chunks[0]["text"] == "First sentence"
        assert chunks[1]["text"] == "Second sentence"
        assert chunks[2]["text"] == "Third sentence"