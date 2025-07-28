"""
Tests for the validation module.
"""
import pytest
from unittest.mock import Mock, patch
import io
import json

from src.processing.validation import DocumentValidator


class TestDocumentValidator:
    """Test DocumentValidator class."""
    
    def test_validate_text_file(self):
        """Test validating a text file."""
        content = b"This is a test document."
        file = io.BytesIO(content)
        
        result = DocumentValidator.validate_file(file, "test.txt")
        
        assert result["is_valid"] is True
        assert result["file_type"] == "txt"
        assert result["mime_type"] == "text/plain"
        assert result["file_size"] == len(content)
        assert "file_hash" in result
    
    def test_validate_pdf_file(self):
        """Test validating a PDF file."""
        # Mock PDF content (simplified)
        content = b"%PDF-1.4 mock pdf content"
        file = io.BytesIO(content)
        
        result = DocumentValidator.validate_file(file, "test.pdf")
        
        assert result["is_valid"] is True
        assert result["file_type"] == "pdf"
        assert result["mime_type"] == "application/pdf"
    
    def test_validate_json_file(self):
        """Test validating a JSON file."""
        content = b'{"test": "data"}'
        file = io.BytesIO(content)
        
        result = DocumentValidator.validate_file(file, "test.json")
        
        assert result["is_valid"] is True
        assert result["file_type"] == "json"
        assert result["mime_type"] == "application/json"
    
    def test_reject_invalid_file_type(self):
        """Test rejecting unsupported file types."""
        content = b"Binary content"
        file = io.BytesIO(content)
        
        with pytest.raises(ValueError, match="Unsupported file type"):
            DocumentValidator.validate_file(file, "test.exe")
    
    def test_reject_large_file(self):
        """Test rejecting files exceeding size limit."""
        # Create file larger than 50MB limit
        large_content = b"x" * (51 * 1024 * 1024)
        file = io.BytesIO(large_content)
        
        with pytest.raises(ValueError, match="exceeds maximum allowed size"):
            DocumentValidator.validate_file(file, "large.txt")
    
    def test_reject_empty_file(self):
        """Test rejecting empty files."""
        file = io.BytesIO(b"")
        
        with pytest.raises(ValueError, match="File is empty"):
            DocumentValidator.validate_file(file, "empty.txt")
    
    def test_validate_content_valid_text(self):
        """Test validating valid text content."""
        result = DocumentValidator.validate_content("Valid text content", "text")
        assert result is True
    
    def test_validate_content_valid_json(self):
        """Test validating valid JSON content."""
        json_content = '{"key": "value", "number": 42}'
        result = DocumentValidator.validate_content(json_content, "json")
        assert result is True
    
    def test_validate_content_invalid_json(self):
        """Test validating invalid JSON content."""
        invalid_json = '{"key": invalid}'
        
        with pytest.raises(ValueError, match="Invalid JSON content"):
            DocumentValidator.validate_content(invalid_json, "json")
    
    def test_validate_content_empty(self):
        """Test validating empty content."""
        with pytest.raises(ValueError, match="Content is empty"):
            DocumentValidator.validate_content("", "text")
        
        with pytest.raises(ValueError, match="Content is empty"):
            DocumentValidator.validate_content("   ", "text")
    
    def test_calculate_hash(self):
        """Test file hash calculation."""
        content = b"Test content for hashing"
        file = io.BytesIO(content)
        
        hash1 = DocumentValidator.calculate_hash(file)
        file.seek(0)
        hash2 = DocumentValidator.calculate_hash(file)
        
        # Same content should produce same hash
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 produces 64 character hex string
    
    def test_calculate_hash_different_content(self):
        """Test hash calculation for different content."""
        file1 = io.BytesIO(b"Content 1")
        file2 = io.BytesIO(b"Content 2")
        
        hash1 = DocumentValidator.calculate_hash(file1)
        hash2 = DocumentValidator.calculate_hash(file2)
        
        # Different content should produce different hashes
        assert hash1 != hash2
    
    def test_sanitize_metadata_empty(self):
        """Test sanitizing empty metadata."""
        result = DocumentValidator.sanitize_metadata({})
        assert result == {}
        
        result = DocumentValidator.sanitize_metadata(None)
        assert result == {}
    
    def test_sanitize_metadata_removes_none(self):
        """Test that None values are removed from metadata."""
        metadata = {
            "key1": "value1",
            "key2": None,
            "key3": "value3",
            "key4": None
        }
        
        result = DocumentValidator.sanitize_metadata(metadata)
        
        assert result == {"key1": "value1", "key3": "value3"}
        assert "key2" not in result
        assert "key4" not in result
    
    def test_sanitize_metadata_converts_string_fields(self):
        """Test that certain fields are converted to strings."""
        metadata = {
            "filename": 123,
            "document_type": ["pdf"],
            "source": {"type": "upload"},
            "other_field": 456
        }
        
        result = DocumentValidator.sanitize_metadata(metadata)
        
        assert result["filename"] == "123"
        assert result["document_type"] == "['pdf']"
        assert result["source"] == "{'type': 'upload'}"
        assert result["other_field"] == 456  # Non-string fields remain unchanged
    
    def test_file_validation_resets_position(self):
        """Test that file position is reset after validation."""
        content = b"Test content"
        file = io.BytesIO(content)
        
        DocumentValidator.validate_file(file, "test.txt")
        
        # File position should be reset to beginning
        assert file.tell() == 0
        # Should be able to read from beginning
        assert file.read() == content
    
    def test_validate_file_with_special_characters(self):
        """Test validating files with special characters in name."""
        content = b"Content"
        file = io.BytesIO(content)
        
        # Should handle special characters in filename
        result = DocumentValidator.validate_file(file, "test file (2024).txt")
        assert result["is_valid"] is True
        assert result["filename"] == "test file (2024).txt"
    
    def test_validate_file_preserves_original_content(self):
        """Test that validation doesn't modify file content."""
        original_content = b"Original file content that should not be modified"
        file = io.BytesIO(original_content)
        
        DocumentValidator.validate_file(file, "test.txt")
        
        # Read content again
        file.seek(0)
        content_after = file.read()
        
        assert content_after == original_content