## Key Principles for Claude Code

### 1. Keep Code Simple
- Use straightforward Python patterns without over-engineering
- Prefer clear, readable code over clever optimizations
- Use explicit imports rather than wildcard imports
- Minimize dependencies - only use what's necessary
- Write functions that do one thing well
- Avoid deep nesting and complex control flows

### 2. Clean Development Practices
- **Always delete unused tests, scripts, and data files**
- **Update README.md or documentation files when making changes**
- Remove commented-out code before committing
- Clean up temporary files and debugging outputs
- Keep the output directories organized and clean

### 3. Automonous refactoring
- Keep codebase as small as possible, avoid adding unnecessary features
- Regularly refactor codebase (e.g. when you did feature updates) to keep it lean and simple

---

# RAG System Project Context

## Project Overview
This is a production-ready Retrieval-Augmented Generation (RAG) system built as a coding challenge. The system demonstrates end-to-end LLM inference pipeline with MLOps best practices.

## Key Components

### 1. Document Processing Pipeline
- Supports PDF, TXT, and JSON formats
- Three chunking strategies: fixed-size, semantic, and sliding window
- Async processing with Redis queue
- Document deduplication and validation

### 2. Vector Storage
- Qdrant vector database for embeddings
- Hybrid search (vector + keyword/BM25)
- Configurable similarity threshold
- Metadata filtering and faceted search

### 3. API Endpoints
- `POST /ingest` - Upload and process documents
- `POST /query` - RAG search with LLM generation
- `GET /documents` - List processed documents
- `DELETE /documents/{id}` - Remove documents
- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics

### 4. Key Features
- Rate limiting (100 req/min)
- Correlation ID tracking
- Structured JSON logging
- Prometheus metrics
- Docker containerization
- Streamlit UI for testing

## Environment Variables
Required in `.env`:
- `OPENAI_API_KEY` - For embeddings and LLM generation
- Other configs have defaults in `src/config.py`

## Testing Commands
```bash
# Install dependencies
source .venv/bin/activate
uv pip install -r requirements.txt

# Run tests
pytest src/tests/ -v --cov=src

# Run API server
uvicorn src.api.main:app --reload

# Run with Docker
docker-compose up

# Lint and format
black src/
isort src/
mypy src/
```

## Architecture Decisions
1. **FastAPI** - Modern async framework with automatic OpenAPI docs
2. **Qdrant** - Efficient vector DB with hybrid search support
3. **Sentence Transformers** - Fast local embeddings (fallback to OpenAI)
4. **Redis** - Async job queue for document processing
5. **Structlog** - Structured logging for production debugging
6. **Prometheus** - Industry-standard metrics collection

## Performance Targets
- Document processing: <5s per MB
- Query latency: <500ms p95
- Embedding generation: Batch processing for efficiency
- API throughput: 100+ req/s

## Security Considerations
- File validation and size limits (50MB)
- Rate limiting per IP
- Input sanitization
- No secrets in code (use .env)
