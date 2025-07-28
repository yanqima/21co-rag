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
6. **Monitoring System**: Added Redis-based logging with correlation ID tracking

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

---

## Monitoring & Observability Implementation (NEW)

### Overview
Complete request tracing system using correlation IDs and Redis-based log storage.

### Backend Components

#### 1. Correlation ID Middleware
- Every request gets a unique UUID
- Added to request state and response headers
- Flows through entire request lifecycle

#### 2. Redis Log Processor
```python
# src/monitoring/logger.py
class RedisLogProcessor:
    - Saves all structured logs to Redis
    - 1-hour TTL for automatic cleanup
    - Maintains recent logs list (max 1000)
    - Creates correlation ID indexes
```

#### 3. Enhanced Logging
- Added detailed logging throughout document processing:
  - `document_ingestion_started`
  - `text_extraction_started/completed`
  - `chunking_started/completed`
  - `embeddings_generation_started/completed`
  - `vector_storage_started/completed`
  - `document_processing_completed`
- All logs include correlation ID for tracing

#### 4. Logs API Endpoint
- `GET /api/v1/logs` - Retrieve system logs
  - Filter by correlation ID
  - Filter by log level
  - Configurable limit
  - Returns structured JSON

### Frontend Components

#### System Logs Tab (Streamlit)
New 6th tab with comprehensive log viewing:

1. **Filtering Options**:
   - Correlation ID input
   - Log level selector
   - Number of logs slider
   - Auto-refresh checkbox

2. **Three View Modes**:
   - **Table View**: Sortable, searchable DataFrame
   - **Timeline View**: Visual flow with color-coded levels
   - **Statistics View**: Log distribution and analysis

3. **Features**:
   - Real-time updates (5-second auto-refresh)
   - Full JSON log details viewer
   - Help section with usage instructions

### How to Get Correlation IDs

1. **From Browser Developer Tools**:
   ```
   Network Tab → Select request → Response Headers → X-Correlation-ID
   ```

2. **Using Test Script**:
   ```bash
   python test_logging.py
   # Returns correlation ID for testing
   ```

3. **Programmatically**:
   ```python
   response = requests.post("http://localhost:8000/api/v1/ingest", ...)
   correlation_id = response.headers.get("X-Correlation-ID")
   ```

### Example Request Trace
For correlation ID `ab80135b-13d2-42a5-8913-bf0df78eb0f4`:
```
1. request_started (0ms)
2. document_ingestion_started (13ms)
3. text_extraction_started (18ms)
4. text_extraction_completed (24ms)
5. chunking_started (30ms)
6. chunking_completed (35ms)
7. embeddings_generation_started (38ms)
8. embeddings_generation_completed (6654ms)
9. vector_storage_started (6659ms)
10. vector_storage_completed (6669ms)
11. document_processing_completed (6671ms)
12. request_completed (6572ms)
```

### Implementation Benefits
- **Debugging**: Trace any request through the entire system
- **Performance Analysis**: Identify bottlenecks (e.g., embedding generation)
- **Error Tracking**: Quick error identification with correlation IDs
- **No External Dependencies**: Uses existing Redis instance
- **Graceful Degradation**: System works even if logging fails

---

## Performance Profiling Implementation (NEW)

### Overview
Zero-overhead performance profiling using existing log data aggregation.

### Backend Components

#### 1. Profiling Module (`src/monitoring/profiling.py`)
Key functions:
- `analyze_request_logs()` - Analyzes logs for single request
- `aggregate_performance_stats()` - Aggregates stats across requests
- `identify_bottlenecks()` - Finds slowest operations

#### 2. Profiling API Endpoint
- `GET /api/v1/profiling` - Returns performance statistics
  - No parameters needed (analyzes last 100 requests)
  - Returns aggregated stats, bottlenecks, and recommendations

### How It Works

1. **Data Collection**:
   - Reads recent logs from Redis
   - Groups logs by correlation ID
   - Extracts timing from phase transitions (_started/_completed events)

2. **Statistical Analysis**:
   - Calculates min, max, avg, P50, P95 for each phase
   - Computes percentage of total time per phase
   - Identifies top bottlenecks

3. **No Additional Overhead**:
   - Uses existing structured logs
   - No new instrumentation
   - No performance impact

### Frontend - Performance Profiling Tab

#### Features:
1. **Overall Metrics**:
   - Total requests analyzed
   - Average, P95, Max request times

2. **Bottleneck Analysis**:
   - Table with operation timings
   - Visual progress bars
   - Color coding: Red (>50%), Orange (20-50%), Blue (<20%)

3. **Phase Statistics**:
   - Tabs for each operation
   - Min/Max/Avg/P50 times

4. **Recent Timeline**:
   - Last 10 requests
   - Correlation IDs and durations

5. **Smart Recommendations**:
   - Automatic based on bottlenecks
   - Specific optimization suggestions

### Example Findings
From real profiling data:
```
Phase                  Avg Time    % of Total
embeddings_generation  6.257s      89.9%
text_extraction       0.006s       0.1%
chunking              0.006s       0.1%
vector_storage        0.012s       0.2%
request (overhead)    0.697s       9.7%
```

### Performance Insights
- **Embedding generation** is the primary bottleneck (70-90%)
- **All other operations** are relatively fast (<1% each)
- **Request overhead** includes FastAPI routing and middleware

### Optimization Opportunities
Based on profiling data:
1. **Cache embeddings** for common text chunks
2. **Use local models** (e.g., sentence-transformers) instead of API
3. **Batch embedding requests** to reduce API calls
4. **Pre-compute embeddings** for static content
- Easy debugging with REST endpoints