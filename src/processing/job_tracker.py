"""
Job tracking for batch processing using Redis.
"""
import json
import redis
from typing import Dict, Any, Optional
from datetime import datetime
import uuid
from src.config import settings
from src.monitoring.logger import get_logger

logger = get_logger(__name__)


class JobTracker:
    """Track batch processing jobs in Redis."""
    
    def __init__(self):
        self.redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            decode_responses=True
        )
        self.job_ttl = 86400  # 24 hours
    
    def create_job(self, total_documents: int) -> str:
        """Create a new job and return job_id."""
        job_id = str(uuid.uuid4())
        job_data = {
            "job_id": job_id,
            "status": "processing",
            "total": total_documents,
            "completed": 0,
            "failed": 0,
            "current_file": "",
            "created_at": datetime.now().isoformat(),
            "documents": {}
        }
        
        self.redis_client.setex(
            f"job:{job_id}",
            self.job_ttl,
            json.dumps(job_data)
        )
        
        logger.info("job_created", job_id=job_id, total=total_documents)
        return job_id
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job data by ID."""
        data = self.redis_client.get(f"job:{job_id}")
        if data:
            return json.loads(data)
        return None
    
    def update_job_progress(
        self,
        job_id: str,
        current_file: str,
        document_id: str,
        status: str,
        error: Optional[str] = None
    ):
        """Update job progress for a document."""
        job_data = self.get_job(job_id)
        if not job_data:
            logger.error("job_not_found", job_id=job_id)
            return
        
        # Update current file
        job_data["current_file"] = current_file
        
        # Update document status
        job_data["documents"][document_id] = {
            "filename": current_file,
            "status": status,
            "error": error
        }
        
        # Update counters
        if status == "completed":
            job_data["completed"] += 1
        elif status == "failed":
            job_data["failed"] += 1
        
        # Check if job is complete
        total_processed = job_data["completed"] + job_data["failed"]
        if total_processed >= job_data["total"]:
            job_data["status"] = "completed"
            job_data["current_file"] = ""
        
        # Save back to Redis
        self.redis_client.setex(
            f"job:{job_id}",
            self.job_ttl,
            json.dumps(job_data)
        )
        
        logger.info(
            "job_progress_updated",
            job_id=job_id,
            file=current_file,
            status=status,
            progress=f"{total_processed}/{job_data['total']}"
        )
    
    def mark_job_failed(self, job_id: str, error: str):
        """Mark entire job as failed."""
        job_data = self.get_job(job_id)
        if job_data:
            job_data["status"] = "failed"
            job_data["error"] = error
            self.redis_client.setex(
                f"job:{job_id}",
                self.job_ttl,
                json.dumps(job_data)
            )