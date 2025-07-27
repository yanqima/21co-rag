import pytest
import io
from src.processing.validation import DocumentValidator, SUPPORTED_FORMATS, MAX_FILE_SIZE


def test_validate_file_success():
    """Test successful file validation."""
    # Create a mock text file
    file_content = b"This is a test document"
    file = io.BytesIO(file_content)
    
    result = DocumentValidator.validate_file(file, "test.txt")
    
    assert result["is_valid"] is True
    assert result["file_type"] == "txt"
    assert result["file_size"] == len(file_content)
    assert "file_hash" in result


def test_validate_file_unsupported_type():
    """Test validation with unsupported file type."""
    file = io.BytesIO(b"test content")
    
    with pytest.raises(ValueError, match="Unsupported file type"):
        DocumentValidator.validate_file(file, "test.exe")


def test_validate_file_too_large():
    """Test validation with file exceeding size limit."""
    # Create a file larger than MAX_FILE_SIZE
    large_content = b"x" * (MAX_FILE_SIZE + 1)
    file = io.BytesIO(large_content)
    
    with pytest.raises(ValueError, match="exceeds maximum allowed size"):
        DocumentValidator.validate_file(file, "large.txt")


def test_validate_file_empty():
    """Test validation with empty file."""
    file = io.BytesIO(b"")
    
    with pytest.raises(ValueError, match="File is empty"):
        DocumentValidator.validate_file(file, "empty.txt")


def test_calculate_hash():
    """Test file hash calculation."""
    content = b"Test content for hashing"
    file = io.BytesIO(content)
    
    hash1 = DocumentValidator.calculate_hash(file)
    
    # Reset file pointer and calculate again
    file.seek(0)
    hash2 = DocumentValidator.calculate_hash(file)
    
    # Same content should produce same hash
    assert hash1 == hash2
    assert len(hash1) == 64  # SHA-256 produces 64 character hex string


def test_validate_content_success():
    """Test successful content validation."""
    # Valid text content
    assert DocumentValidator.validate_content("Valid text content", "txt") is True
    
    # Valid JSON content
    json_content = '{"key": "value"}'
    assert DocumentValidator.validate_content(json_content, "json") is True


def test_validate_content_empty():
    """Test content validation with empty content."""
    with pytest.raises(ValueError, match="Content is empty"):
        DocumentValidator.validate_content("", "txt")
    
    with pytest.raises(ValueError, match="Content is empty"):
        DocumentValidator.validate_content("   ", "txt")


def test_validate_content_invalid_json():
    """Test content validation with invalid JSON."""
    with pytest.raises(ValueError, match="Invalid JSON content"):
        DocumentValidator.validate_content("{invalid json}", "json")


def test_sanitize_metadata():
    """Test metadata sanitization."""
    # Test with various metadata
    metadata = {
        "filename": "test.txt",
        "document_type": "text",
        "source": 123,  # Should be converted to string
        "empty_field": None,  # Should be removed
        "valid_field": "value"
    }
    
    sanitized = DocumentValidator.sanitize_metadata(metadata)
    
    assert sanitized["filename"] == "test.txt"
    assert sanitized["source"] == "123"  # Converted to string
    assert "empty_field" not in sanitized  # None values removed
    assert sanitized["valid_field"] == "value"
    
    # Test with None metadata
    assert DocumentValidator.sanitize_metadata(None) == {}