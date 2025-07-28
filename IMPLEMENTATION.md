# RAG System Implementation Details

## Current Architecture

### Core Components

#### 1. Document Processing Pipeline
- **Chunking Strategies** (via LangChain):
  - `sliding_window`: CharacterTextSplitter with overlap
  - `sentence`: RecursiveCharacterTextSplitter
  - `semantic`: SemanticChunker using OpenAI embeddings
- **File Support**: PDF, TXT, JSON
- **Validation**: File size (<50MB), format checking, content validation
- **Background Processing**: FastAPI BackgroundTasks

#### 2. Vector Storage (Qdrant)
- **Collection**: "documents" 
- **Embedding Model**: sentence-transformers/all-MiniLM-L6-v2 (384 dimensions)
- **Search Types**:
  - Vector similarity search
  - Hybrid search (vector + keyword with substring matching)
- **Default Similarity Threshold**: 0.4 (configurable)

#### 3. ReAct Agent (LangChain)
- **Agent Type**: CHAT_CONVERSATIONAL_REACT_DESCRIPTION
- **Tools**:
  - `search_documents`: Searches vector store for content
  - `get_system_info`: Returns document count and metadata
- **Memory**: ConversationBufferMemory
- **Behavior**: Intelligently routes queries to appropriate tools

#### 4. API Endpoints
- `POST /api/v1/ingest` - Single document upload
- `POST /api/v1/batch-ingest` - Multiple document upload with job tracking
- `GET /api/v1/jobs/{job_id}` - Get batch job status
- `POST /api/v1/query` - Search with optional RAG generation
- `GET /api/v1/documents` - List all documents
- `DELETE /api/v1/documents/{id}` - Remove document
- `GET /api/v1/health` - Health check
- `GET /api/v1/metrics` - Prometheus metrics

#### 5. Streamlit UI
- **Upload Documents**: Single file upload with chunking options
- **Batch Upload**: Multi-file upload with real-time progress tracking
- **Search & Query**: Advanced search with adjustable parameters
- **Document Library**: View and manage documents
- **Chat Interface**: Conversational interaction with documents
- **Sidebar Config**: API URL and similarity threshold settings

### Configuration (src/config.py)
- `similarity_threshold`: 0.4 (lowered from 0.7 for better recall)
- `chunk_size`: 512
- `chunk_overlap`: 50
- `embedding_dimension`: 384
- `rate_limit_per_minute`: 100

### Recent Updates
1. **Similarity Threshold**: Lowered from 0.7 to 0.4 for better partial match support
2. **Keyword Matching**: Improved to use substring matching instead of exact word matching
3. **ReAct Agent**: Complete rewrite using LangChain for better tool selection
4. **Source Attribution**: Fixed to properly track and return source chunks
5. **UI Configuration**: Added similarity threshold slider in Streamlit sidebar

---

## Batch Processing Implementation (NEW)

### Overview
Simple batch document processing with progress tracking using polling approach.

### Backend Components

#### 1. Job Tracking (Redis)
```python
# Job structure in Redis (24-hour TTL)
{
    "job_id": "uuid",
    "status": "processing",  # or "completed", "failed"
    "total": 100,
    "completed": 45,
    "failed": 2,
    "current_file": "document_46.pdf",
    "created_at": timestamp,
    "documents": {
        "doc_id_1": {"filename": "file1.pdf", "status": "completed"},
        "doc_id_2": {"filename": "file2.pdf", "status": "failed", "error": "..."}
    }
}
```

#### 2. New API Endpoints
- `POST /api/v1/batch-ingest` - Upload multiple files
  - Accepts: List of files, chunking strategy
  - Returns: job_id for tracking
- `GET /api/v1/jobs/{job_id}` - Poll job status
  - Returns: Current job state and progress

#### 3. Concurrency Control
- Config: `max_concurrent_documents` (default: 5)
- Uses asyncio.Semaphore for limiting concurrent processing
- Updates Redis after each document

### Frontend Components

#### 1. Batch Upload Tab (Streamlit)
- Multi-file uploader with drag-and-drop
- Single chunking strategy selector for all files
- File list with remove option
- Progress tracking after upload

#### 2. Progress Display
- Progress bar showing percentage complete
- Current file being processed
- Document status table:
  - ⏳ Pending
  - 🔄 Processing
  - ✅ Completed
  - ❌ Failed (with error details)
- Auto-refresh every 2 seconds via polling
- Toast notification on completion

### Implementation Flow
1. User selects multiple files in new "Batch Upload" tab
2. System creates job and returns job_id
3. Background task processes files with concurrency limit
4. Frontend polls `/api/v1/jobs/{job_id}` every 2 seconds
5. Progress updates shown in real-time
6. Toast notification when complete

### Benefits
- No new dependencies (uses existing stack)
- Simple polling instead of WebSocket complexity
- Natural Streamlit rerun for updates
- Minimal state management with Redis TTL
- Easy debugging with REST endpoints