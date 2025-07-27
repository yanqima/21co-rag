import pytest
from src.processing.chunking import (
    FixedSizeChunking, 
    SemanticChunking, 
    SlidingWindowChunking,
    ChunkingFactory
)


def test_fixed_size_chunking():
    """Test fixed-size chunking strategy."""
    text = "This is a test document. " * 20  # ~500 characters
    chunker = FixedSizeChunking(chunk_size=100, overlap=20)
    
    chunks = chunker.chunk(text)
    
    assert len(chunks) > 0
    assert all("text" in chunk for chunk in chunks)
    assert all("chunk_id" in chunk for chunk in chunks)
    
    # Check overlap
    if len(chunks) > 1:
        # Last 20 chars of first chunk should be in second chunk
        overlap_text = chunks[0]["text"][-20:]
        assert overlap_text in chunks[1]["text"]


def test_semantic_chunking():
    """Test semantic chunking strategy."""
    text = """This is paragraph one.
    It contains multiple sentences.
    
    This is paragraph two.
    It also has multiple sentences.
    
    This is paragraph three."""
    
    chunker = SemanticChunking(max_chunk_size=100)
    chunks = chunker.chunk(text)
    
    assert len(chunks) > 0
    assert all("text" in chunk for chunk in chunks)
    
    # Should respect paragraph boundaries
    assert any("\n\n" not in chunk["text"] for chunk in chunks)


def test_sliding_window_chunking():
    """Test sliding window chunking strategy."""
    text = "A" * 200  # 200 characters
    chunker = SlidingWindowChunking(window_size=50, stride=25)
    
    chunks = chunker.chunk(text)
    
    assert len(chunks) > 0
    
    # Check window overlap
    if len(chunks) > 1:
        # Windows should overlap by 25 characters
        assert chunks[0]["text"][25:] == chunks[1]["text"][:25]


def test_chunking_factory():
    """Test chunking factory."""
    # Test creating different strategies
    fixed_chunker = ChunkingFactory.create_strategy("fixed", chunk_size=100)
    assert isinstance(fixed_chunker, FixedSizeChunking)
    
    semantic_chunker = ChunkingFactory.create_strategy("semantic")
    assert isinstance(semantic_chunker, SemanticChunking)
    
    sliding_chunker = ChunkingFactory.create_strategy("sliding_window")
    assert isinstance(sliding_chunker, SlidingWindowChunking)
    
    # Test invalid strategy
    with pytest.raises(ValueError):
        ChunkingFactory.create_strategy("invalid_strategy")


def test_empty_text_handling():
    """Test handling of empty text."""
    chunker = FixedSizeChunking()
    
    # Empty string
    assert chunker.chunk("") == []
    
    # None text (should handle gracefully)
    assert chunker.chunk(None) == []


def test_metadata_preservation():
    """Test that metadata is preserved in chunks."""
    text = "Test document content"
    metadata = {"document_id": "123", "source": "test"}
    
    chunker = FixedSizeChunking(chunk_size=10)
    chunks = chunker.chunk(text, metadata)
    
    assert all(chunk["metadata"] == metadata for chunk in chunks)