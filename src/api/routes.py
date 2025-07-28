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

# Initialize components
vector_store = VectorStore()
embedding_generator = EmbeddingGenerator()
document_validator = DocumentValidator()
job_tracker = JobTracker()

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
        validation_result = document_validator.validate_file(
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
        document_validator.validate_content(text, validation_result["file_type"])
        
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
        
        embeddings_data = await embedding_generator.generate_embeddings(
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
        
        await vector_store.upsert_documents(embeddings_data)
        
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
        async def search_function(query_embedding, search_type, limit, filters, similarity_threshold):
            if search_type == "vector":
                return await vector_store.search(
                    query_embedding=query_embedding,
                    limit=limit,
                    filters=filters,
                    similarity_threshold=similarity_threshold
                )
            else:  # hybrid
                return await vector_store.hybrid_search(
                    query_embedding=query_embedding,
                    query_text=request.query,
                    limit=limit,
                    filters=filters,
                    similarity_threshold=similarity_threshold
                )
        
        # Generate embedding for query (needed for search)
        query_embeddings = await embedding_generator.generate_embeddings([request.query])
        query_embedding = query_embeddings[0]["embedding"]
        
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
                vector_store=vector_store
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
        logger.error("query_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Query processing failed")


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
        
        # Generate answer using OpenAI
        import openai
        from openai import AsyncOpenAI
        
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that answers questions based on the provided context."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        return response.choices[0].message.content
        
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
        documents, total = await vector_store.list_documents(offset, limit)
        
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
        success = await vector_store.delete_document(document_id)
        
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
    job_id = job_tracker.create_job(len(files))
    
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
            job_tracker.update_job_progress(
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
    job_data = job_tracker.get_job(job_id)
    
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
                job_tracker.update_job_progress(
                    job_id=job_id,
                    current_file=filename,
                    document_id=document_id,
                    status="processing"
                )
                
                # Validate file
                import io
                file_obj = io.BytesIO(file_info["content"])
                validation_result = document_validator.validate_file(
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
                job_tracker.update_job_progress(
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
                job_tracker.update_job_progress(
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
        job_tracker.mark_job_failed(job_id, str(e))


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