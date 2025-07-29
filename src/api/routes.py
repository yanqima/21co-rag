from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Request, BackgroundTasks
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import uuid
import json
from datetime import datetime

from src.processing.validation import DocumentValidator
from src.processing.chunking import ChunkingFactory
from src.processing.embeddings import EmbeddingGenerator
from src.storage.vector_db import VectorStore
from src.monitoring.logger import get_logger
from src.monitoring.metrics import get_metrics, active_processing_jobs
from src.config import settings
from src.processing.job_tracker import JobTracker
import asyncio
import redis

logger = get_logger(__name__)

# Global component instances (lazy initialization)
_vector_store = None
_embedding_generator = None
_document_validator = None
_job_tracker = None

def get_vector_store():
    """Get vector store instance with lazy initialization."""
    global _vector_store
    if _vector_store is None:
        try:
            logger.info("Initializing VectorStore...")
            _vector_store = VectorStore()
            logger.info("VectorStore initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize VectorStore: {str(e)}")
            raise
    return _vector_store

def get_embedding_generator():
    """Get embedding generator instance with lazy initialization."""
    global _embedding_generator
    if _embedding_generator is None:
        _embedding_generator = EmbeddingGenerator()
    return _embedding_generator

def get_document_validator():
    """Get document validator instance with lazy initialization."""
    global _document_validator
    if _document_validator is None:
        _document_validator = DocumentValidator()
    return _document_validator

def get_job_tracker():
    """Get job tracker instance with lazy initialization."""
    global _job_tracker
    if _job_tracker is None:
        _job_tracker = JobTracker()
    return _job_tracker

# Create routers
router = APIRouter()


# Pydantic models
class IngestResponse(BaseModel):
    job_id: str
    message: str
    document_id: str


class QueryRequest(BaseModel):
    query: str = Field(..., description="Search query")
    limit: int = Field(default=10, ge=1, le=100)
    similarity_threshold: float = Field(default=settings.similarity_threshold, ge=0.0, le=1.0)
    search_type: str = Field(default="hybrid", pattern="^(vector|keyword|hybrid)$")
    filters: Optional[Dict[str, Any]] = None
    generate_answer: bool = Field(default=True)
    session_id: Optional[str] = Field(default="default", description="Session ID for conversation memory")


class QueryResponse(BaseModel):
    results: List[Dict[str, Any]]
    answer: Optional[str] = None
    total_results: int
    search_type: str
    processing_time: float


class DocumentResponse(BaseModel):
    documents: List[Dict[str, Any]]
    total: int
    offset: int
    limit: int


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str = "1.0.0"


class BatchIngestResponse(BaseModel):
    job_id: str
    message: str
    total_files: int


class JobStatus(BaseModel):
    job_id: str
    status: str
    total: int
    completed: int
    failed: int
    current_file: str
    created_at: str
    documents: Dict[str, Any]


class LogEntry(BaseModel):
    timestamp: str
    level: str
    event: str
    correlation_id: Optional[str]
    message: Optional[str]
    data: Dict[str, Any]


class LogsResponse(BaseModel):
    logs: List[Dict[str, Any]]
    count: int
    filtered_by: Optional[str] = None


@router.post("/ingest", response_model=IngestResponse)
async def ingest_document(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    chunking_strategy: str = "sliding_window",
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None
):
    """Upload and process a document."""
    job_id = str(uuid.uuid4())
    
    try:
        # Validate file
        validation_result = get_document_validator().validate_file(
            file.file, 
            file.filename
        )
        
        # Generate document ID
        document_id = str(uuid.uuid4())
        
        # Get correlation ID from request
        correlation_id = getattr(request.state, "correlation_id", None)
        
        # Add background task for processing
        background_tasks.add_task(
            process_document,
            file_content=await file.read(),
            document_id=document_id,
            validation_result=validation_result,
            chunking_strategy=chunking_strategy,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            correlation_id=correlation_id
        )
        
        logger.info(
            "document_ingestion_started",
            correlation_id=correlation_id,
            job_id=job_id,
            document_id=document_id,
            filename=file.filename
        )
        
        return IngestResponse(
            job_id=job_id,
            message="Document processing started",
            document_id=document_id
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("document_ingestion_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Document ingestion failed")


async def process_document(
    file_content: bytes,
    document_id: str,
    validation_result: Dict[str, Any],
    chunking_strategy: str,
    chunk_size: Optional[int],
    chunk_overlap: Optional[int],
    correlation_id: Optional[str] = None
):
    """Process document in background."""
    active_processing_jobs.inc()
    
    try:
        # Extract text based on file type
        logger.info(
            "text_extraction_started",
            correlation_id=correlation_id,
            document_id=document_id,
            file_type=validation_result["file_type"]
        )
        
        if validation_result["file_type"] == "pdf":
            text = extract_pdf_text(file_content)
        elif validation_result["file_type"] == "txt":
            text = file_content.decode("utf-8")
        elif validation_result["file_type"] == "json":
            import json
            data = json.loads(file_content)
            text = json.dumps(data, indent=2)
        else:
            raise ValueError(f"Unsupported file type: {validation_result['file_type']}")
        
        logger.info(
            "text_extraction_completed",
            correlation_id=correlation_id,
            document_id=document_id,
            text_length=len(text)
        )
        
        # Validate content
        get_document_validator().validate_content(text, validation_result["file_type"])
        
        # Create chunking strategy
        chunker = ChunkingFactory.create_strategy(
            chunking_strategy,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        
        # Chunk the text
        logger.info(
            "chunking_started",
            correlation_id=correlation_id,
            document_id=document_id,
            strategy=chunking_strategy
        )
        
        chunks = chunker.chunk(
            text,
            metadata={
                "document_id": document_id,
                "filename": validation_result["filename"],
                "document_type": validation_result["file_type"],
                "file_hash": validation_result["file_hash"]
            }
        )
        
        logger.info(
            "chunking_completed",
            correlation_id=correlation_id,
            document_id=document_id,
            chunks_count=len(chunks)
        )
        
        # Generate embeddings
        logger.info(
            "embeddings_generation_started",
            correlation_id=correlation_id,
            document_id=document_id,
            chunks_count=len(chunks)
        )
        
        texts = [chunk["text"] for chunk in chunks]
        chunk_metadata = [chunk["metadata"] for chunk in chunks]
        
        embeddings_data = await get_embedding_generator().generate_embeddings(
            texts, 
            chunk_metadata
        )
        
        logger.info(
            "embeddings_generation_completed",
            correlation_id=correlation_id,
            document_id=document_id,
            embeddings_count=len(embeddings_data)
        )
        
        # Store in vector database
        logger.info(
            "vector_storage_started",
            correlation_id=correlation_id,
            document_id=document_id
        )
        
        await get_vector_store().upsert_documents(embeddings_data)
        
        logger.info(
            "vector_storage_completed",
            correlation_id=correlation_id,
            document_id=document_id
        )
        
        logger.info(
            "document_processing_completed",
            correlation_id=correlation_id,
            document_id=document_id,
            chunks_count=len(chunks),
            filename=validation_result["filename"]
        )
        
    except Exception as e:
        logger.error(
            "document_processing_failed",
            correlation_id=correlation_id,
            document_id=document_id,
            error=str(e)
        )
    finally:
        active_processing_jobs.dec()


def extract_pdf_text(content: bytes) -> str:
    """Extract text from PDF content."""
    import io
    from PyPDF2 import PdfReader
    
    pdf_file = io.BytesIO(content)
    reader = PdfReader(pdf_file)
    
    text = ""
    for page_num in range(len(reader.pages)):
        page = reader.pages[page_num]
        text += page.extract_text() + "\n"
    
    return text


@router.post("/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    """Search documents and generate RAG response using ReAct agent."""
    import time
    from src.processing.react_agent import process_query_with_agent
    
    start_time = time.time()
    
    try:
        # Define search function for the agent
        async def search_function(query_embedding, search_type, limit, filters, similarity_threshold, query_text=None):
            if search_type == "vector":
                return await get_vector_store().search(
                    query_embedding=query_embedding,
                    limit=limit,
                    filters=filters,
                    similarity_threshold=similarity_threshold
                )
            else:  # hybrid
                # Use provided query_text or fall back to request.query
                text_query = query_text if query_text is not None else request.query
                return await get_vector_store().hybrid_search(
                    query_embedding=query_embedding,
                    query_text=text_query,
                    limit=limit,
                    filters=filters,
                    similarity_threshold=similarity_threshold
                )
        
        # Generate embedding for query (needed for search)
        query_embeddings = await get_embedding_generator().generate_embeddings([request.query])
        query_embedding = query_embeddings[0]["embedding"]  # Extract the embedding list from the result
        
        # Prepare search parameters
        search_params = {
            "query_embedding": query_embedding,
            "search_type": request.search_type,
            "limit": request.limit,
            "filters": request.filters,
            "similarity_threshold": request.similarity_threshold
        }
        
        # Process query with ReAct agent
        if request.generate_answer:
            agent_result = await process_query_with_agent(
                query=request.query,
                search_function=search_function,
                search_params=search_params,
                vector_store=get_vector_store(),
                embedding_generator=get_embedding_generator(),
                session_id=request.session_id or "default"
            )
            
            processing_time = time.time() - start_time
            
            return QueryResponse(
                results=agent_result["results"],
                answer=agent_result["answer"],
                total_results=agent_result["total_results"],
                search_type=request.search_type,
                processing_time=processing_time
            )
        else:
            # Fallback to original search-only behavior
            results = await search_function(**search_params)
            processing_time = time.time() - start_time
            
            return QueryResponse(
                results=results,
                answer=None,
                total_results=len(results),
                search_type=request.search_type,
                processing_time=processing_time
            )
        
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.error("query_failed", error=str(e), traceback=tb)
        raise HTTPException(status_code=500, detail=f"Query processing failed: {str(e)}")


async def generate_rag_answer(query: str, results: List[Dict[str, Any]]) -> str:
    """Generate answer using RAG approach."""
    try:
        # Prepare context from search results
        context_texts = []
        for i, result in enumerate(results[:5]):  # Use top 5 results
            context_texts.append(f"[{i+1}] {result['text']}")
        
        context = "\n\n".join(context_texts)
        
        # Create prompt
        prompt = f"""Based on the following context, answer the question. If the answer cannot be found in the context, say so.

Context:
{context}

Question: {query}

Answer:"""
        
        # Generate answer using direct HTTP call to OpenAI API
        import httpx
        import json
        
        headers = {
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": settings.openai_model,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant that answers questions based on the provided context."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 500
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30.0
            )
            response.raise_for_status()
            result = response.json()
            
        return result["choices"][0]["message"]["content"]
        
    except Exception as e:
        logger.error("answer_generation_failed", error=str(e))
        return "Failed to generate answer"


@router.get("/documents", response_model=DocumentResponse)
async def list_documents(
    offset: int = 0,
    limit: int = 50
):
    """List all processed documents."""
    try:
        documents, total = await get_vector_store().list_documents(offset, limit)
        
        return DocumentResponse(
            documents=documents,
            total=total,
            offset=offset,
            limit=limit
        )
        
    except Exception as e:
        logger.error("list_documents_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list documents")


@router.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    """Delete a document and its embeddings."""
    try:
        success = await get_vector_store().delete_document(document_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return {"message": "Document deleted successfully", "document_id": document_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("delete_document_failed", document_id=document_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to delete document")


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat()
    )


@router.get("/metrics")
async def get_metrics_endpoint():
    """Prometheus metrics endpoint."""
    metrics = get_metrics()
    return Response(content=metrics, media_type="text/plain")


@router.post("/batch-ingest", response_model=BatchIngestResponse)
async def batch_ingest_documents(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    chunking_strategy: str = "sliding_window",
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
    processing_delay: Optional[float] = None
):
    """Upload and process multiple documents in batch."""
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    if len(files) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 files allowed per batch")
    
    # Create job
    job_id = get_job_tracker().create_job(len(files))
    
    # Read all file contents first
    file_data = []
    for file in files:
        try:
            content = await file.read()
            file_data.append({
                "content": content,
                "filename": file.filename,
                "content_type": file.content_type
            })
        except Exception as e:
            logger.error("file_read_failed", filename=file.filename, error=str(e))
            get_job_tracker().update_job_progress(
                job_id=job_id,
                current_file=file.filename,
                document_id=str(uuid.uuid4()),
                status="failed",
                error=f"Failed to read file: {str(e)}"
            )
    
    # Queue batch processing
    background_tasks.add_task(
        process_batch_documents,
        job_id=job_id,
        file_data=file_data,
        chunking_strategy=chunking_strategy,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        processing_delay=processing_delay or settings.batch_processing_delay
    )
    
    logger.info(
        "batch_ingestion_started",
        job_id=job_id,
        file_count=len(files)
    )
    
    return BatchIngestResponse(
        job_id=job_id,
        message="Batch processing started",
        total_files=len(files)
    )


@router.get("/jobs/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    """Get status of a batch processing job."""
    job_data = get_job_tracker().get_job(job_id)
    
    if not job_data:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return JobStatus(**job_data)


async def process_batch_documents(
    job_id: str,
    file_data: List[Dict[str, Any]],
    chunking_strategy: str,
    chunk_size: Optional[int],
    chunk_overlap: Optional[int],
    processing_delay: float = 1.0
):
    """Process multiple documents with concurrency control."""
    semaphore = asyncio.Semaphore(settings.max_concurrent_documents)
    
    async def process_one_document(file_info: Dict[str, Any]):
        async with semaphore:
            document_id = str(uuid.uuid4())
            filename = file_info["filename"]
            
            try:
                # Update current file
                get_job_tracker().update_job_progress(
                    job_id=job_id,
                    current_file=filename,
                    document_id=document_id,
                    status="processing"
                )
                
                # Validate file
                import io
                file_obj = io.BytesIO(file_info["content"])
                validation_result = get_document_validator().validate_file(
                    file_obj,
                    filename
                )
                
                # Process document (similar to single document processing)
                await process_document(
                    file_content=file_info["content"],
                    document_id=document_id,
                    validation_result=validation_result,
                    chunking_strategy=chunking_strategy,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap
                )
                
                # Mark as completed
                get_job_tracker().update_job_progress(
                    job_id=job_id,
                    current_file=filename,
                    document_id=document_id,
                    status="completed"
                )
                
                # Add artificial delay for demo purposes
                if processing_delay > 0:
                    await asyncio.sleep(processing_delay)
                
            except Exception as e:
                logger.error(
                    "batch_document_processing_failed",
                    job_id=job_id,
                    filename=filename,
                    error=str(e)
                )
                get_job_tracker().update_job_progress(
                    job_id=job_id,
                    current_file=filename,
                    document_id=document_id,
                    status="failed",
                    error=str(e)
                )
                
                # Add delay even for failed documents
                if processing_delay > 0:
                    await asyncio.sleep(processing_delay)
    
    # Process all documents concurrently
    try:
        await asyncio.gather(
            *[process_one_document(file_info) for file_info in file_data],
            return_exceptions=True
        )
    except Exception as e:
        logger.error("batch_processing_failed", job_id=job_id, error=str(e))
        get_job_tracker().mark_job_failed(job_id, str(e))


@router.get("/logs", response_model=LogsResponse)
async def get_logs(
    correlation_id: Optional[str] = None,
    limit: int = 100,
    level: Optional[str] = None
):
    """Get system logs from Redis."""
    try:
        redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            decode_responses=True
        )
        
        logs = []
        
        if correlation_id:
            # Get logs for specific correlation ID
            corr_key = f"logs:correlation:{correlation_id}"
            log_keys = redis_client.lrange(corr_key, 0, limit - 1)
            filtered_by = f"correlation_id: {correlation_id}"
        else:
            # Get recent logs
            log_keys = redis_client.lrange("logs:recent", 0, limit - 1)
            filtered_by = None
        
        # Fetch log entries
        for log_key in log_keys:
            log_data = redis_client.get(log_key)
            if log_data:
                try:
                    log_entry = json.loads(log_data)
                    
                    # Filter by level if specified
                    if level and log_entry.get("level", "").lower() != level.lower():
                        continue
                        
                    logs.append(log_entry)
                except json.JSONDecodeError:
                    logger.warning("invalid_log_entry", key=log_key)
        
        if level and not correlation_id:
            filtered_by = f"level: {level}"
        elif level and correlation_id:
            filtered_by = f"correlation_id: {correlation_id}, level: {level}"
        
        return LogsResponse(
            logs=logs,
            count=len(logs),
            filtered_by=filtered_by
        )
        
    except Exception as e:
        logger.error("get_logs_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve logs")


@router.get("/profiling")
async def get_profiling_stats(
    time_range: Optional[int] = 100  # Number of recent requests to analyze
):
    """Get performance profiling statistics from logs."""
    try:
        from src.monitoring.profiling import aggregate_performance_stats, identify_bottlenecks
        
        # Get recent logs
        redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            decode_responses=True
        )
        
        # Fetch more logs than requested to ensure we get complete requests
        log_keys = redis_client.lrange("logs:recent", 0, time_range * 20)
        
        all_logs = []
        for log_key in log_keys:
            log_data = redis_client.get(log_key)
            if log_data:
                try:
                    log_entry = json.loads(log_data)
                    all_logs.append(log_entry)
                except json.JSONDecodeError:
                    continue
        
        # Analyze performance
        stats = aggregate_performance_stats(all_logs)
        
        # Identify bottlenecks
        bottlenecks = []
        if stats['phase_stats']:
            bottlenecks = identify_bottlenecks(stats['phase_stats'])
        
        return {
            'stats': stats,
            'bottlenecks': bottlenecks,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error("get_profiling_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get profiling stats")


@router.post("/admin/recreate-collection")
async def recreate_collection():
    """Temporary endpoint to recreate Qdrant collection with correct dimension."""
    try:
        vector_store = get_vector_store()
        
        # Delete existing collection if it exists
        try:
            collections = vector_store.client.get_collections().collections
            if any(c.name == vector_store.collection_name for c in collections):
                logger.info(f"Deleting existing collection {vector_store.collection_name}")
                vector_store.client.delete_collection(vector_store.collection_name)
        except Exception as e:
            logger.warning(f"Error deleting collection: {str(e)}")
        
        # Recreate collection with correct dimension
        from qdrant_client.models import VectorParams, Distance
        logger.info(f"Creating collection {vector_store.collection_name} with dimension {settings.embedding_dimension}")
        
        vector_store.client.create_collection(
            collection_name=vector_store.collection_name,
            vectors_config=VectorParams(
                size=settings.embedding_dimension,
                distance=Distance.COSINE
            )
        )
        
        # Create payload indices for filtering
        vector_store.client.create_payload_index(
            collection_name=vector_store.collection_name,
            field_name="document_id",
            field_schema="keyword"
        )
        
        vector_store.client.create_payload_index(
            collection_name=vector_store.collection_name,
            field_name="document_type",
            field_schema="keyword"
        )
        
        return {
            "message": f"Collection {vector_store.collection_name} recreated successfully",
            "dimension": settings.embedding_dimension
        }
        
    except Exception as e:
        logger.error(f"Failed to recreate collection: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to recreate collection: {str(e)}")


@router.get("/admin/test-redis")
async def test_redis_connection():
    """Test Redis connection and basic operations."""
    try:
        import redis
        redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            decode_responses=True
        )
        
        # Test basic operations
        test_key = "test:connection"
        test_value = "test_value"
        
        # Set a value
        redis_client.set(test_key, test_value, ex=60)
        
        # Get the value
        retrieved_value = redis_client.get(test_key)
        
        # Clean up
        redis_client.delete(test_key)
        
        return {
            "status": "success",
            "redis_host": settings.redis_host,
            "redis_port": settings.redis_port,
            "redis_db": settings.redis_db,
            "test_result": retrieved_value == test_value
        }
        
    except Exception as e:
        logger.error(f"Redis connection test failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "redis_host": settings.redis_host,
            "redis_port": settings.redis_port,
            "redis_db": settings.redis_db
        }


@router.post("/admin/test-embedding")
async def test_embedding_generation():
    """Test embedding generation with a simple text."""
    try:
        embedding_generator = get_embedding_generator()
        
        # First, let's check the configuration
        config_info = {
            "model_name": embedding_generator.model_name,
            "batch_size": embedding_generator.batch_size,
            "openai_api_key_set": bool(settings.openai_api_key),
            "embedding_dimension": settings.embedding_dimension
        }
        
        test_text = "This is a test document for embedding generation."
        
        try:
            # Generate embedding
            embeddings = await embedding_generator.generate_embeddings([test_text])
            
            if embeddings and len(embeddings) > 0:
                embedding = embeddings[0]
                return {
                    "status": "success",
                    "text": test_text,
                    "embedding_dimension": len(embedding["embedding"]),
                    "expected_dimension": settings.embedding_dimension,
                    "dimension_match": len(embedding["embedding"]) == settings.embedding_dimension,
                    "config": config_info
                }
            else:
                return {
                    "status": "error",
                    "error": "No embeddings generated",
                    "config": config_info
                }
        except Exception as embedding_error:
            return {
                "status": "error",
                "error": f"Embedding generation failed: {str(embedding_error)}",
                "config": config_info,
                "error_type": type(embedding_error).__name__
            }
        
    except Exception as e:
        logger.error(f"Embedding generation test failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__
        }


@router.post("/admin/test-openai-direct")
async def test_openai_direct():
    """Test OpenAI API directly to isolate the issue."""
    try:
        import openai
        from openai import AsyncOpenAI
        
        # Try different client initialization approaches
        try:
            # Method 1: Simple initialization
            client = AsyncOpenAI(api_key=settings.openai_api_key)
            init_method = "simple"
        except Exception as init_error:
            try:
                # Method 2: Clear any global config first
                openai.api_key = None
                client = AsyncOpenAI(api_key=settings.openai_api_key)
                init_method = "cleared_global"
            except Exception as init_error2:
                return {
                    "status": "error",
                    "error": f"Client initialization failed: {str(init_error)} | {str(init_error2)}",
                    "error_type": "InitializationError",
                    "model_attempted": settings.embedding_model
                }
        
        test_text = "This is a test document for embedding generation."
        
        # Test the direct OpenAI API call
        response = await client.embeddings.create(
            model=settings.embedding_model,
            input=[test_text]
        )
        
        embedding = response.data[0].embedding
        
        return {
            "status": "success",
            "model_used": settings.embedding_model,
            "embedding_dimension": len(embedding),
            "expected_dimension": settings.embedding_dimension,
            "dimension_match": len(embedding) == settings.embedding_dimension,
            "text": test_text,
            "init_method": init_method
        }
        
    except Exception as e:
        logger.error(f"Direct OpenAI API test failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__,
            "model_attempted": settings.embedding_model
        }


@router.post("/admin/test-openai-isolated")
async def test_openai_isolated():
    """Test OpenAI API in complete isolation from other imports."""
    try:
        # Import in a completely fresh way
        import sys
        import importlib
        
        # Remove any cached openai modules
        modules_to_remove = [k for k in sys.modules.keys() if k.startswith('openai')]
        for module in modules_to_remove:
            if module in sys.modules:
                del sys.modules[module]
        
        # Fresh import
        openai_module = importlib.import_module('openai')
        OpenAI = getattr(openai_module, 'OpenAI')  # Use synchronous client
        
        # Create synchronous client with explicit args only
        try:
            # Method 1: Only api_key
            client = OpenAI(api_key=settings.openai_api_key)
            init_method = "api_key_only"
        except Exception as e1:
            try:
                # Method 2: Use **kwargs to filter
                kwargs = {"api_key": settings.openai_api_key}
                client = OpenAI(**kwargs)
                init_method = "kwargs_filtered"
            except Exception as e2:
                return {
                    "status": "error",
                    "error": f"All client init methods failed: {str(e1)} | {str(e2)}",
                    "error_type": "ClientInitError",
                    "model_attempted": settings.embedding_model,
                    "method": "isolated_import"
                }
        
        test_text = "This is a test document for embedding generation."
        
        # Test the API call (synchronous)
        response = client.embeddings.create(
            model=settings.embedding_model,
            input=[test_text]
        )
        
        embedding = response.data[0].embedding
        
        return {
            "status": "success",
            "model_used": settings.embedding_model,
            "embedding_dimension": len(embedding),
            "expected_dimension": settings.embedding_dimension,
            "dimension_match": len(embedding) == settings.embedding_dimension,
            "text": test_text,
            "method": "isolated_import",
            "init_method": init_method
        }
        
    except Exception as e:
        logger.error(f"Isolated OpenAI API test failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__,
            "model_attempted": settings.embedding_model,
            "method": "isolated_import"
        }


@router.post("/admin/test-openai-http")
async def test_openai_http():
    """Test OpenAI API using direct HTTP requests to bypass client library issues."""
    try:
        import httpx
        import json
        
        test_text = "This is a test document for embedding generation."
        
        # Direct HTTP call to OpenAI API
        headers = {
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": settings.embedding_model,
            "input": [test_text]
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers=headers,
                json=data,
                timeout=30.0
            )
            
            if response.status_code == 200:
                result = response.json()
                embedding = result["data"][0]["embedding"]
                
                return {
                    "status": "success",
                    "model_used": settings.embedding_model,
                    "embedding_dimension": len(embedding),
                    "expected_dimension": settings.embedding_dimension,
                    "dimension_match": len(embedding) == settings.embedding_dimension,
                    "text": test_text,
                    "method": "direct_http"
                }
            else:
                return {
                    "status": "error",
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "error_type": "HTTPError",
                    "model_attempted": settings.embedding_model,
                    "method": "direct_http"
                }
        
    except Exception as e:
        logger.error(f"Direct HTTP OpenAI API test failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__,
            "model_attempted": settings.embedding_model,
            "method": "direct_http"
        }


@router.post("/admin/test-react-agent")
async def test_react_agent():
    """Test ReAct agent initialization and basic functionality."""
    try:
        from src.processing.react_agent import process_query_with_agent
        
        # Simple test query
        test_query = "Hello, can you help me?"
        
        # Mock search function for testing
        async def mock_search_function(query_embedding, search_type, limit, filters, similarity_threshold):
            return [{
                "id": "test-id",
                "score": 0.9,
                "text": "This is a test document for the RAG system.",
                "metadata": {
                    "document_id": "test-doc-id",
                    "filename": "test.txt",
                    "chunk_id": 0
                }
            }]
        
        # Mock search params
        search_params = {
            "query_embedding": [0.1] * 1536,  # Mock embedding
            "search_type": "hybrid",
            "limit": 5,
            "filters": None,
            "similarity_threshold": 0.7
        }
        
        # Test the agent
        result = await process_query_with_agent(
            query=test_query,
            search_function=mock_search_function,
            search_params=search_params,
            vector_store=get_vector_store()
        )
        
        return {
            "status": "success",
            "query": test_query,
            "agent_response": result,
            "method": "react_agent_test"
        }
        
    except Exception as e:
        logger.error(f"ReAct agent test failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__,
            "method": "react_agent_test"
        }


@router.post("/admin/test-llm-direct")
async def test_llm_direct():
    """Test LLM initialization and direct call."""
    try:
        from langchain_openai import ChatOpenAI
        from langchain.schema import HumanMessage
        
        # Test LangChain ChatOpenAI initialization
        llm = ChatOpenAI(
            model=settings.openai_model,
            temperature=0.7,
            api_key=settings.openai_api_key
        )
        
        # Test a simple call
        test_message = HumanMessage(content="Hello, this is a test. Please respond with 'Test successful'.")
        response = await llm.agenerate([[test_message]])
        
        return {
            "status": "success",
            "model_used": settings.openai_model,
            "response": response.generations[0][0].text,
            "method": "langchain_llm_test"
        }
        
    except Exception as e:
        logger.error(f"LangChain LLM test failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__,
            "method": "langchain_llm_test"
        }