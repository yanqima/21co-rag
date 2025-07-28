# Production-Ready RAG System

A production-ready Retrieval-Augmented Generation (RAG) system built with FastAPI, Qdrant, and OpenAI. Features a beautiful Streamlit UI for demonstrations and comprehensive MLOps best practices.

## 🚀 Quick Start

```bash
# One-command demo launch
./run_demo.sh
```

This starts all services and opens the Streamlit UI at http://localhost:8501

## 🎯 Project Overview

### What's Implemented

✅ **Complete RAG Pipeline** - Document ingestion, vector storage, semantic search, and AI-powered answer generation  
✅ **Production Features** - Monitoring, logging, error handling, rate limiting, and Docker deployment  
✅ **Beautiful UI** - Professional Streamlit interface with real-time feedback and smooth animations  
✅ **Comprehensive Testing** - Unit tests, integration tests, and performance benchmarks  

### Key Capabilities

- **Multi-format Support**: PDF, TXT, JSON document processing
- **Smart Chunking**: Fixed-size, semantic, and sliding window strategies
- **Hybrid Search**: Combines vector similarity with keyword matching
- **Async Processing**: Background jobs with progress tracking
- **Scalable Architecture**: Horizontally scalable with proper separation of concerns

## 📋 Features

### Document Processing
- **File Types**: PDF, TXT, JSON (extensible to more formats)
- **Chunking Strategies** (Powered by LangChain):
  - Sliding Window (default): Character-based chunks with configurable overlap
  - Sentence/Paragraph: Respects natural text boundaries using RecursiveCharacterTextSplitter
  - Semantic: Uses OpenAI embeddings to create semantically coherent chunks
- **Validation**: File size limits (50MB), format checking, content deduplication
- **Background Processing**: Async pipeline with Redis queue

### Vector Storage & Search
- **Vector Database**: Qdrant with 1536-dimensional OpenAI embeddings
- **Search Types**:
  - Vector similarity search
  - Keyword search (BM25)
  - Hybrid search (configurable blend)
- **Advanced Features**:
  - Similarity threshold configuration (0.0-1.0)
  - Metadata filtering
  - Batch processing for efficiency

### API Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/ingest` | POST | Upload and process single document |
| `/api/v1/batch-ingest` | POST | Upload and process multiple documents |
| `/api/v1/jobs/{job_id}` | GET | Get batch job status |
| `/api/v1/query` | POST | Search and generate AI answers |
| `/api/v1/documents` | GET | List all documents |
| `/api/v1/documents/{id}` | DELETE | Remove document |
| `/api/v1/health` | GET | Health check |
| `/api/v1/metrics` | GET | Prometheus metrics |

### Streamlit UI
- **Document Upload**: Single file upload with drag-and-drop
- **Batch Upload**: Multi-file upload with progress tracking
- **Search Interface**: Natural language queries with AI responses
- **Document Library**: Manage uploaded documents
- **Chat Interface**: Conversational interaction with your knowledge base
- **Advanced Controls**: Fine-tune search parameters live

### Production Features
- **Monitoring**: 
  - Prometheus metrics (latency, throughput, error rates)
  - Structured JSON logging with correlation IDs
  - Redis-based log storage for UI display
  - Real-time log viewer in Streamlit
- **Security**: Rate limiting (100 req/min), input validation
- **Performance**: <500ms query latency, concurrent processing
- **Deployment**: Docker multi-stage builds, Kubernetes-ready
- **Documentation**: OpenAPI specs, comprehensive guides

### Intelligent ReAct Agent
- **LangChain ReAct Pattern**: Reasoning and Acting agent that intelligently handles queries
- **Available Tools**:
  - `search_documents`: Searches uploaded documents for relevant information
  - `get_system_info`: Retrieves system metadata (document count, list)
- **Smart Response Logic**:
  - Greetings → Direct response without tool use
  - Content questions → Uses search_documents tool
  - System queries → Uses get_system_info tool
- **Context Aware**: Maintains conversation memory using LangChain's ConversationBufferMemory
- **Source Attribution**: Returns relevant document chunks with relevance scores

### Batch Document Processing (NEW)
- **Multi-file Upload**: Process up to 100 documents in a single batch
- **Real-time Progress Tracking**: 
  - Live progress bar showing completion percentage
  - Document-by-document status updates
  - Current file being processed indicator
- **Concurrent Processing**: Configurable concurrency limit (default: 5 documents)
- **Job Management**: Redis-based job tracking with 24-hour TTL
- **Configurable Delay**: Artificial processing delay for demo purposes (0-5 seconds)
- **Error Handling**: Individual document failures don't stop the batch
- **Progress Polling**: Auto-refresh every 2 seconds to show live updates

### System Monitoring & Observability (NEW)
- **Correlation ID Tracking**: Every request gets a unique ID for end-to-end tracing
- **Comprehensive Logging**: 
  - All processing phases logged with correlation IDs
  - Stored in Redis with 1-hour TTL
  - Accessible via `/api/v1/logs` endpoint
- **Log Viewer UI**: 
  - Filter by correlation ID or log level
  - Table, timeline, and statistics views
  - Real-time auto-refresh option
  - Full JSON log details
- **Request Lifecycle Visibility**:
  - Track documents from upload through embedding generation
  - Monitor processing times for each phase
  - Identify bottlenecks and errors quickly

### Performance Profiling Dashboard (NEW)
- **Real-time Performance Analytics**: 
  - Aggregates timing data from system logs
  - No additional overhead - uses existing log data
  - Accessible via `/api/v1/profiling` endpoint
- **Metrics & Visualizations**:
  - Overall performance stats (Avg, P95, Max times)
  - Bottleneck analysis with visual progress bars
  - Phase-by-phase breakdown with statistics
  - Recent request timeline
- **Smart Recommendations**:
  - Automatic bottleneck detection
  - Targeted optimization suggestions
  - Performance degradation alerts
- **Zero-overhead Implementation**:
  - Reuses existing correlation ID logs
  - No additional instrumentation needed
  - Simple aggregation from Redis

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Streamlit UI                          │
│         (Beautiful frontend for demonstrations)          │
└─────────────────────────┬───────────────────────────────┘
                          │ HTTP/REST
                          ▼
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Backend                       │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │   Routes    │  │  Processing  │  │  Background   │  │
│  │  & Auth     │  │   Pipeline   │  │     Jobs      │  │
│  └─────────────┘  └──────────────┘  └───────────────┘  │
└────────┬──────────────────┬──────────────────┬─────────┘
         │                  │                  │
         ▼                  ▼                  ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│     Qdrant      │ │     Redis       │ │    OpenAI       │
│   Vector DB     │ │     Queue       │ │      API        │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

## 🛠️ Installation

### Prerequisites
- Python 3.10+
- Docker and Docker Compose
- OpenAI API key

### Option 1: Local Development (Recommended)

You can run the system in different configurations using Docker Compose profiles:

1. **Clone and setup**:
   ```bash
   git clone <repository-url>
   cd 21co-rag
   cp .env.example .env
   # Edit .env with your OpenAI API key
   ```

2. **Choose your deployment mode**:

   **🏠 Infrastructure Only (Recommended for Development)**:
   ```bash
   ./start-local.sh infra
   # Then run apps natively for hot-reload:
   pip install -r requirements.txt
   uvicorn src.api.main:app --reload --port 8000  # Terminal 1
   streamlit run streamlit_app.py --server.port 8501  # Terminal 2
   ```

   **🐳 Full Docker Stack**:
   ```bash
   ./start-local.sh full
   # Everything runs in containers with volume mounts for development
   ```

   **⚙️ Applications Only** (if infrastructure already running):
   ```bash
   ./start-local.sh apps
   ```

3. **Access the application**:
   - Streamlit UI: http://localhost:8501
   - API Documentation: http://localhost:8000/docs
   - Qdrant Dashboard: http://localhost:6333/dashboard

4. **Stop services**:
   ```bash
   ./stop-local.sh [infra|apps|full|all]
   ```

### Option 2: GCP Cloud Run Deployment

For production deployment using serverless GCP services:

1. **Setup cloud services**:
   - Create Qdrant Cloud cluster
   - Create GCP Cloud Memorystore Redis instance
   - Configure `.env.gcp` with your credentials

2. **Deploy to Cloud Run**:
   ```bash
   # Edit PROJECT_ID in deploy-gcp.sh first
   ./deploy-gcp.sh
   ```

3. **Services used**:
   - **Cloud Run**: Serverless containers for API and Streamlit
   - **Qdrant Cloud**: Managed vector database
   - **Cloud Memorystore**: Managed Redis
   - **No Docker Compose needed** - everything is serverless!

## 🎮 Using the System

### 1. Streamlit UI (Recommended for Demos)

The Streamlit interface provides an intuitive way to interact with the RAG system:

#### **Document Upload Tab**
- Drag and drop files or browse to select
- Choose chunking strategy based on document type
- Watch real-time processing progress
- Supports PDF, TXT, and JSON files

#### **Search & Query Tab**
- Enter natural language questions
- Get AI-generated answers with source citations
- Adjust search parameters:
  - **Search Type**: Hybrid, Vector, or Keyword
  - **Similarity Threshold**: Control result relevance
  - **Result Count**: Number of sources to retrieve
- View performance metrics

#### **Document Library Tab**
- See all uploaded documents
- View metadata and chunk counts
- Delete documents with one click
- Track upload timestamps

#### **Chat Interface Tab**
- Have conversations with your documents
- Maintains chat history
- Shows source attributions
- Context-aware responses

### 2. API Usage

#### Upload a Document
```bash
curl -X POST "http://localhost:8000/api/v1/ingest" \
  -F "file=@document.pdf" \
  -F "chunking_strategy=semantic"
```

#### Search and Generate Answer
```bash
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is machine learning?",
    "generate_answer": true,
    "limit": 5
  }'
```

#### List Documents
```bash
curl "http://localhost:8000/api/v1/documents"
```

### 3. API Documentation

Interactive API docs available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🧪 Testing

### Run Tests
```bash
# Unit tests with coverage
pytest src/tests/ -v --cov=src

# Specific test categories
pytest src/tests/test_chunking.py -v
pytest src/tests/test_api.py -v
```

### Performance Benchmarks
- Document Processing: ~1-2s per document
- Query Latency: 300-650ms (including LLM)
- Vector Search: <20ms
- Throughput: 100+ requests/second

## 🚢 Deployment

### Docker Deployment
```bash
# Build image
docker build -f docker/Dockerfile -t rag-api .

# Run container
docker run -p 8000:8000 --env-file .env rag-api
```

### Production Deployment

See [deployment guide](handover/deployment_guide.md) for:
- AWS ECS/Fargate deployment
- Kubernetes deployment
- Monitoring setup
- Scaling strategies

## 📊 Configuration

Key environment variables:

```env
# API Settings
API_HOST=0.0.0.0
API_PORT=8000
ENVIRONMENT=production

# OpenAI
OPENAI_API_KEY=your-key
OPENAI_MODEL=gpt-3.5-turbo
EMBEDDING_MODEL=text-embedding-ada-002

# Vector Database
QDRANT_HOST=localhost
QDRANT_PORT=6333
COLLECTION_NAME=documents

# Search Settings
SIMILARITY_THRESHOLD=0.7
SEARCH_LIMIT=10
HYBRID_SEARCH_ALPHA=0.5

# Performance
CHUNK_SIZE=512
CHUNK_OVERLAP=50
BATCH_SIZE=32
MAX_FILE_SIZE_MB=50
```

## 🎯 Demo Guide

### Preparing for Demo

1. **Start fresh**:
```bash
docker compose down -v
./run_demo.sh
```

2. **Upload sample documents**:
- Use files in `sample_data/` directory
- Mix of PDF, TXT, and JSON files
- Shows different content types

### Demo Script

#### 1. **Show System Health**
- Click "Check Health" in sidebar
- Demonstrates monitoring capabilities

#### 2. **Document Upload Demo**
- Upload a PDF file
- Show real-time progress
- Explain chunking strategies

#### 3. **Search Capabilities**
- Simple query: "What is machine learning?"
- Complex query: "Compare supervised and unsupervised learning"
- Show source attribution

#### 4. **Advanced Features**
- Adjust similarity threshold
- Switch search types
- Show performance metrics

#### 5. **Chat Interface**
- Natural conversation flow
- Context retention
- Source transparency

#### 6. **System Monitoring Demo** (NEW)
- **Getting a Correlation ID**:
  - Upload any document or make a search query
  - Check browser's Network tab → Response Headers → `X-Correlation-ID`
  - Or use the test script: `python test_logging.py`
- **Tracing a Request**:
  - Go to System Logs tab
  - Paste the correlation ID
  - Show complete request lifecycle
  - Demonstrate the three view modes
- **Real-time Monitoring**:
  - Enable auto-refresh
  - Upload a document in another tab
  - Watch logs appear in real-time

#### 7. **Performance Profiling Demo** (NEW)
- **Analyze System Performance**:
  - Go to Performance Profiling tab
  - Click "Analyze Performance"
  - Review bottleneck analysis
- **Key Insights to Highlight**:
  - Embedding generation takes 70-90% of time
  - Visual progress bars show time distribution
  - P95 vs average times reveal outliers
- **Optimization Discussion**:
  - Review automatic recommendations
  - Discuss caching strategies
  - Consider local embedding models

### Key Talking Points

✅ **Production Ready**: Monitoring, logging, error handling  
✅ **Scalable**: Async processing, horizontal scaling  
✅ **Flexible**: Multiple file formats, search strategies  
✅ **User Friendly**: Beautiful UI, intuitive controls  
✅ **Performant**: Sub-second responses, efficient processing  

## 🐛 Troubleshooting

### Common Issues

**Services won't start**
```bash
# Check ports
lsof -i :8000,8501,6333,6379

# Restart everything
docker compose down
./run_demo.sh
```

**Upload fails**
- Check file size (<50MB)
- Verify file format (PDF, TXT, JSON)
- Check API logs: `docker compose logs api`

**No search results**
- Lower similarity threshold
- Try different search type
- Verify documents were processed

**Streamlit connection error**
- Ensure API is running: `curl http://localhost:8000/api/v1/health`
- Check API URL in sidebar configuration
- Refresh the page

## 📂 Project Structure

```
21co-rag/
├── src/                    # Application source code
│   ├── api/               # FastAPI routes and middleware
│   ├── processing/        # Document processing pipeline
│   ├── storage/           # Vector database interface
│   ├── monitoring/        # Logging and metrics
│   └── tests/            # Unit and integration tests
├── docker/                # Docker configuration
│   ├── Dockerfile        # Multi-stage build
│   └── docker-compose.yml # Local development setup
├── sample_data/          # Example documents for testing
├── handover/             # Detailed documentation
│   ├── HANDOVER.md      # Project handover letter
│   ├── architecture_diagram.md
│   └── deployment_guide.md
├── streamlit_app.py      # Streamlit UI application
├── run_demo.sh          # Demo launcher script
├── requirements.txt      # Python dependencies
├── .env.example         # Environment variables template
└── README.md            # This file
```

## 🔒 Security Considerations

- Input validation on all endpoints
- File size and type restrictions
- Rate limiting (100 req/min default)
- Ready for authentication layer (JWT)
- Secrets management via environment variables
- Non-root Docker user

## 🎯 Next Steps

### Immediate Enhancements
1. Add JWT authentication
2. Implement caching layer
3. Add more file formats (DOCX, HTML)

### Future Features
1. Multi-tenant support
2. Document versioning
3. Semantic caching
4. Fine-tuning support
5. A/B testing framework

## 📚 Additional Resources

- [Architecture Overview](handover/architecture_diagram.md)
- [Deployment Guide](handover/deployment_guide.md)
- [API Documentation](http://localhost:8000/docs)
- [Handover Letter](handover/HANDOVER.md)

## 🤝 Acknowledgments

Built as a technical assessment for 21co, demonstrating production-ready ML infrastructure with modern best practices.

---

**Ready to demo?** Run `./run_demo.sh` and let the system speak for itself! 🚀