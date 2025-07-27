from typing import BinaryIO, Dict, Any, Optional
import hashlib
import mimetypes
from pathlib import Path
from src.monitoring.logger import get_logger

logger = get_logger(__name__)

# Supported file types
SUPPORTED_FORMATS = {
    "application/pdf": "pdf",
    "text/plain": "txt",
    "application/json": "json",
}

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


class DocumentValidator:
    """Validate documents before processing."""
    
    @staticmethod
    def validate_file(file: BinaryIO, filename: str) -> Dict[str, Any]:
        """Validate uploaded file."""
        # Check file extension
        file_ext = Path(filename).suffix.lower()
        
        # Check MIME type
        mime_type = mimetypes.guess_type(filename)[0]
        
        if mime_type not in SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported file type: {mime_type}. Supported types: {list(SUPPORTED_FORMATS.values())}")
        
        # Check file size
        file.seek(0, 2)  # Seek to end
        file_size = file.tell()
        file.seek(0)  # Reset to beginning
        
        if file_size > MAX_FILE_SIZE:
            raise ValueError(f"File size ({file_size} bytes) exceeds maximum allowed size ({MAX_FILE_SIZE} bytes)")
        
        if file_size == 0:
            raise ValueError("File is empty")
        
        # Calculate file hash
        file_hash = DocumentValidator.calculate_hash(file)
        file.seek(0)  # Reset again
        
        validation_result = {
            "filename": filename,
            "file_type": SUPPORTED_FORMATS[mime_type],
            "mime_type": mime_type,
            "file_size": file_size,
            "file_hash": file_hash,
            "is_valid": True
        }
        
        logger.info("file_validated", **validation_result)
        
        return validation_result
    
    @staticmethod
    def calculate_hash(file: BinaryIO) -> str:
        """Calculate SHA-256 hash of file content."""
        sha256_hash = hashlib.sha256()
        
        # Read file in chunks
        for chunk in iter(lambda: file.read(4096), b""):
            sha256_hash.update(chunk)
        
        return sha256_hash.hexdigest()
    
    @staticmethod
    def validate_content(content: str, content_type: str) -> bool:
        """Validate content based on type."""
        if not content or not content.strip():
            raise ValueError("Content is empty")
        
        if content_type == "json":
            try:
                import json
                json.loads(content)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON content: {str(e)}")
        
        return True
    
    @staticmethod
    def sanitize_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize and validate metadata."""
        if not metadata:
            return {}
        
        # Remove None values
        sanitized = {k: v for k, v in metadata.items() if v is not None}
        
        # Ensure string values for certain fields
        string_fields = ["filename", "document_type", "source"]
        for field in string_fields:
            if field in sanitized and not isinstance(sanitized[field], str):
                sanitized[field] = str(sanitized[field])
        
        return sanitized