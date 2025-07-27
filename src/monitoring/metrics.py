from prometheus_client import Counter, Histogram, Gauge, generate_latest
from typing import Dict, Any
import time
from functools import wraps


# Define metrics
request_count = Counter(
    'rag_api_requests_total',
    'Total number of API requests',
    ['method', 'endpoint', 'status']
)

request_duration = Histogram(
    'rag_api_request_duration_seconds',
    'API request duration in seconds',
    ['method', 'endpoint']
)

document_processing_count = Counter(
    'rag_documents_processed_total',
    'Total number of documents processed',
    ['status']
)

document_processing_duration = Histogram(
    'rag_document_processing_duration_seconds',
    'Document processing duration in seconds',
    ['document_type']
)

embedding_generation_duration = Histogram(
    'rag_embedding_generation_duration_seconds',
    'Embedding generation duration in seconds'
)

vector_search_duration = Histogram(
    'rag_vector_search_duration_seconds',
    'Vector search duration in seconds',
    ['search_type']
)

active_processing_jobs = Gauge(
    'rag_active_processing_jobs',
    'Number of active document processing jobs'
)

vector_db_size = Gauge(
    'rag_vector_db_documents',
    'Number of documents in vector database'
)

error_count = Counter(
    'rag_errors_total',
    'Total number of errors',
    ['error_type', 'endpoint']
)


def track_request(method: str, endpoint: str, status_code: int, duration: float):
    """Track API request metrics."""
    request_count.labels(method=method, endpoint=endpoint, status=status_code).inc()
    request_duration.labels(method=method, endpoint=endpoint).observe(duration)


def track_document_processing(status: str, duration: float, doc_type: str):
    """Track document processing metrics."""
    document_processing_count.labels(status=status).inc()
    document_processing_duration.labels(document_type=doc_type).observe(duration)


def track_embedding_generation(duration: float):
    """Track embedding generation metrics."""
    embedding_generation_duration.observe(duration)


def track_vector_search(search_type: str, duration: float):
    """Track vector search metrics."""
    vector_search_duration.labels(search_type=search_type).observe(duration)


def track_error(error_type: str, endpoint: str):
    """Track error metrics."""
    error_count.labels(error_type=error_type, endpoint=endpoint).inc()


def measure_time(metric_func):
    """Decorator to measure function execution time."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                metric_func(duration=duration)
                return result
            except Exception as e:
                duration = time.time() - start_time
                metric_func(duration=duration)
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                metric_func(duration=duration)
                return result
            except Exception as e:
                duration = time.time() - start_time
                metric_func(duration=duration)
                raise
        
        if func.__name__.startswith('async_'):
            return async_wrapper
        return sync_wrapper
    return decorator


def get_metrics() -> bytes:
    """Generate Prometheus metrics."""
    return generate_latest()