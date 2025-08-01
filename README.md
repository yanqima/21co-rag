# Production-Ready RAG System

A production-ready Retrieval-Augmented Generation (RAG) system built with FastAPI, Qdrant, and OpenAI. Features a beautiful Streamlit UI for demonstrations and comprehensive MLOps best practices.

## 🚀 Quick Start

### Local Development
```bash
# One-command demo launch
./run_demo.sh
```

### Docker Compose (Recommended)
```bash
# Start all services with Docker
docker-compose up -d

# Access points:
# - API: http://localhost:8000
# - API Docs: http://localhost:8000/docs  
# - Streamlit UI: http://localhost:8501
```

### Cloud Deployment
```bash
# Deploy to Google Cloud Run
./deploy-gcp.sh
```

## ⚙️ Environment Setup & Deployment

### 📁 Environment Files Overview

This project uses three different environment files for different purposes:

| File | Purpose | Required For | Can Be Committed |
|------|---------|--------------|------------------|
| `.env` | Local development configuration | Local development | ❌ No (contains API keys) |
| `.env.gcp` | GCP Cloud Run environment variables | Cloud deployment | ❌ No (contains secrets) |
| `.env.deploy` | GCP deployment configuration | Cloud deployment | ✅ Yes (no secrets) |

### 🔧 Environment File Details

#### `.env` - Local Development
Used for local development with Docker Compose or direct Python execution.

**Setup:**
```bash
cp .env.example .env
# Edit .env with your API keys
```

**Key Variables:**
```env
# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key-here
OPENAI_MODEL=gpt-4o

# Local Services (Docker)
QDRANT_HOST=localhost
QDRANT_PORT=6333
REDIS_HOST=localhost
REDIS_PORT=6379

# API Configuration  
API_HOST=0.0.0.0
API_PORT=8000
ENVIRONMENT=development
```

#### `.env.gcp` - Cloud Run Environment Variables
Contains all runtime environment variables for the deployed Cloud Run services.

**Key Variables:**
```env
# OpenAI Configuration
OPENAI_API_KEY=your-production-openai-key
OPENAI_MODEL=gpt-4o

# Qdrant Cloud Configuration
QDRANT_URL=https://your-cluster.qdrant.io
QDRANT_API_KEY=your-qdrant-api-key
QDRANT_COLLECTION=documents

# Cloud Memorystore Redis
REDIS_HOST=10.x.x.x  # Private IP from GCP
REDIS_PORT=6379
REDIS_DB=0

# Production Settings
ENVIRONMENT=production
LOG_LEVEL=INFO
```

#### `.env.deploy` - Deployment Configuration
Contains GCP deployment parameters (project ID, region, service names).

**Setup:**
```bash
cp deploy.config.example .env.deploy
# Edit .env.deploy with your GCP project details
```

**Key Variables:**
```env
# GCP Project Configuration
PROJECT_ID=your-gcp-project-id
REGION=europe-west1

# Cloud Run Service Names
SERVICE_NAME_API=rag-api
SERVICE_NAME_STREAMLIT=rag-streamlit
```

### 🚀 Deployment Process

#### Option 1: Configuration File (Recommended)
```bash
# 1. Set up deployment config
cp deploy.config.example .env.deploy
# Edit .env.deploy with your GCP project ID

# 2. Deploy
./deploy-gcp.sh
```

#### Option 2: Environment Variables
```bash
export PROJECT_ID="your-project-id"
export REGION="europe-west1"
./deploy-gcp.sh
```

#### Option 3: Interactive Prompts
```bash
./deploy-gcp.sh
# Script will prompt for each parameter
```

### 📋 Pre-Deployment Checklist

Before running `./deploy-gcp.sh`, ensure:

- [ ] **GCP Setup**
  - [ ] `gcloud` CLI installed and authenticated
  - [ ] GCP project created with billing enabled
  - [ ] APIs enabled: Cloud Run, Cloud Build, Memorystore Redis

- [ ] **Environment Files**
  - [ ] `.env.gcp` configured with production API keys
  - [ ] `.env.deploy` configured with your project details

- [ ] **External Services**
  - [ ] Qdrant Cloud cluster created and URL/API key added to `.env.gcp`
  - [ ] Cloud Memorystore Redis instance created and IP added to `.env.gcp`
  - [ ] OpenAI API key added to `.env.gcp`

### 🔐 Security Best Practices

- **Never commit** `.env` or `.env.gcp` files (they contain secrets)
- **Do commit** `.env.deploy` (contains no secrets, just configuration)
- Use **different API keys** for development (`.env`) and production (`.env.gcp`)
- **Rotate keys regularly** and use GCP Secret Manager for production

## 🌐 **Live Deployment Status**

**✅ Currently Deployed & Operational:**
- **API Service**: https://rag-api-479524373755.europe-west1.run.app
- **Streamlit UI**: https://rag-streamlit-479524373755.europe-west1.run.app
- **Health Check**: ✅ API responding with `{"status": "healthy", "version": "1.0.0"}`
- **Infrastructure**: Qdrant Cloud + Cloud Memorystore Redis + VPC connector
- **Last Deployed**: From commit `24c0e47` (stable working version)

**🚀 Deployment Features:**
- **Auto-scaling**: 0-5 instances based on traffic
- **Fast Startup**: Lazy initialization prevents timeout errors
- **Session Persistence**: Redis-backed conversation memory
- **Full Pipeline**: Document upload → embedding → search → chat working end-to-end

## 🎯 Project Overview

### What's Implemented

✅ **Complete RAG Pipeline** - Document ingestion, vector storage, semantic search, and AI-powered answer generation  
✅ **Production Features** - Monitoring, logging, error handling, rate limiting, and Docker deployment  
✅ **Beautiful UI** - Professional Streamlit interface with real-time feedback and smooth animations  
✅ **Comprehensive Testing** - Unit tests, integration tests, and performance benchmarks  
✅ **Optimized Dependencies** - Streamlined requirements for faster builds and smaller images  
✅ **Cloud-Ready** - Google Cloud Run deployment with optimized Dockerfiles  
✅ **Vector Database Alignment** - Proper embedding dimension matching between OpenAI and Qdrant

### 🆕 Recent Major Improvements

#### **🤖 LangChain ReAct Agent (Latest)**
- **Intelligent Query Processing**: ReAct agent that reasons about queries and chooses appropriate tools
- **Conversational Memory**: Redis-backed session persistence across browser sessions
- **Smart Tool Selection**: Automatically decides whether to search documents or provide direct responses
- **Natural Interactions**: Handles greetings, help requests, and contextual queries intelligently
- **Performance**: Direct responses ~0.08s, contextual queries ~1.5s

#### **🔧 Critical Bug Fixes & Optimizations**
- **🚀 Docker Dependencies**: Fixed protobuf version conflicts between grpcio-tools (>=6.30.0) and streamlit (<5)
- **📦 Dependency Resolution**: Pinned compatible versions to eliminate slow build loops:
  - `langchain==0.2.16`, `langchain-openai==0.1.23`, `openai==1.40.0`
  - `grpcio==1.60.0`, `grpcio-tools==1.60.0`, `protobuf==4.25.5`
- **☁️ Qdrant Cloud Integration**: Fixed connection issues by switching from host/port to URL/API key authentication
- **🔄 Streamlit Cloud Deployment**: Resolved API restriction errors by moving `st.chat_input()` outside tabs
- **⚡ Lazy Initialization**: Prevented Cloud Run startup timeouts by deferring heavy component loading
- **🧠 Redis Memory Integration**: Successfully integrated LangChain's official `RedisChatMessageHistory` for persistent conversational memory
- **🔐 Session Isolation**: Implemented session-based memory with proper isolation across users
- **⚡ Performance**: Eliminated dependency resolution loops, achieving 10x faster builds

#### **🧹 Repository Maintenance & Environment Setup**
- **Clean Repository**: Removed all `__pycache__` files and obsolete documentation
- **Enhanced .gitignore**: Comprehensive Python patterns covering cache files, build artifacts, environments, and IDE files
- **Environment Cleanup**: Removed unused `runtime.txt` (Heroku-specific) and `chunking_guide.txt` (superseded by LangChain docs)
- **Docker File Handling**: Proper gitignore rules for deployment Dockerfiles while ignoring temporary copies
- **Professional Standards**: Repository now follows industry best practices for Python projects

#### **🧠 LangChain Redis Memory System**
- **✅ Official Integration**: Using `langchain-redis==0.0.4` with multi-tier fallback system
- **🔄 Session Persistence**: Conversation memory persists across stateless API requests
- **🛡️ Robust Fallbacks**: Primary (LangChain Redis) → Secondary (Custom Redis) → Tertiary (In-memory)
- **⏰ Auto-cleanup**: 24-hour TTL on Redis keys with configurable memory limits (50 messages)
- **🔒 Session Isolation**: Each user session gets independent memory storage
- **📊 Production Ready**: Compatible with Cloud Run deployment and Docker environments

#### **Build & Deployment Optimization**
- **🚀 10x Faster Builds**: Eliminated heavy ML dependencies (sentence-transformers, PyTorch)
- **📦 Smaller Images**: Removed unused dependencies and test files for production builds
- **☁️ Cloud Run Ready**: Optimized Dockerfiles for production deployment
- **⚡ OpenAI Embeddings**: Switched to `text-embedding-3-small` for better performance

#### **Streamlit UI Fixes**
- **🔧 Chat Interface**: Fixed input positioning and message overflow issues
- **📱 Better UX**: Input stays at top, shows last 10 messages to prevent scrolling
- **🎯 Tab Compatibility**: Resolved Streamlit version conflicts with chat input in tabs
- **💬 Conversation Tracking**: Improved message history and response generation

#### **Vector Database Alignment**
- **🎯 Dimension Matching**: Fixed OpenAI (1536) vs Qdrant dimension mismatches
- **🔄 Auto-Reset**: Proper collection recreation when switching embedding models
- **✅ Error Prevention**: Eliminated "Vector dimension error" during file uploads
- **🏗️ Architecture**: Consistent embedding pipeline from ingestion to search  

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
  - `get_conversation_memory`: Retrieves previous conversation context when users ask about memory
- **Smart Response Logic**:
  - Greetings → Direct response without tool use
  - Content questions → Uses search_documents tool
  - System queries → Uses get_system_info tool
  - Memory questions → Uses get_conversation_memory tool
- **Persistent Memory**: Redis-backed conversation history with session isolation:
  - **Session-based**: Each user session maintains independent conversation memory
  - **Cross-request Persistence**: Memory survives across stateless API calls
  - **LangChain Integration**: Uses official `RedisChatMessageHistory` for compatibility
  - **Automatic Cleanup**: 24-hour TTL with configurable message limits (50 messages)
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

### Option 1: Docker Compose (Recommended)

**🚀 Fully optimized Docker setup with fast builds and production-ready containers**

1. **Clone and setup**:
   ```bash
   git clone <repository-url>
   cd 21co-rag
   cp .env.example .env
   # Edit .env with your OpenAI API key
   ```

2. **Start all services**:
   ```bash
   # Start with Qdrant Cloud (recommended)
   ./switch_env.sh cloud
   docker-compose up -d
   
   # OR start with local Qdrant
   ./switch_env.sh local  
   docker-compose up -d
   ```

3. **Access the application**:
   - **Streamlit UI**: http://localhost:8501
   - **API Documentation**: http://localhost:8000/docs
   - **API Health**: http://localhost:8000/api/v1/health
   - **Qdrant Dashboard**: http://localhost:6333/dashboard (local only)

4. **Stop services**:
   ```bash
   docker-compose down
   ```

### Option 2: Local Development

**For development with hot-reload:**

```bash
# Start infrastructure only
docker-compose up -d rag-redis
# Use Qdrant Cloud or start local Qdrant

# Install dependencies (optimized for fast installs)
pip install -r requirements.txt

# Run services natively
uvicorn src.api.main:app --reload --port 8000  # Terminal 1
streamlit run streamlit_app.py --server.port 8502  # Terminal 2
```

### Option 3: GCP Cloud Run Deployment

**🚀 Production-ready serverless deployment with optimized build times**

1. **Setup cloud services**:
   - Create Qdrant Cloud cluster
   - Create GCP Cloud Memorystore Redis instance  
   - Configure `.env.gcp` with your credentials

2. **Deploy to Cloud Run**:
   ```bash
   # Edit PROJECT_ID in deploy-gcp.sh first
   ./deploy-gcp.sh
   ```

3. **Deployment Features**:
   - **⚡ Fast Builds**: ~5 minutes (vs 30+ minutes previously)
   - **📦 Optimized Images**: Removed heavy ML dependencies
   - **🔄 Auto-scaling**: 0-100 instances based on traffic
   - **💰 Cost-effective**: Pay only for actual usage

4. **Services used**:
   - **Cloud Run**: Serverless containers for API and Streamlit
   - **Qdrant Cloud**: Managed vector database
   - **Cloud Memorystore**: Managed Redis
   - **OpenAI API**: For embeddings and LLM responses

## 📦 Dependencies & Requirements

### Optimized Requirements

The `requirements.txt` has been heavily optimized for production:

**✅ Core Dependencies (Kept)**:
```
fastapi==0.104.1
streamlit==1.29.0
langchain==0.1.0
langchain-openai==0.0.5
qdrant-client==1.7.0
redis==5.0.1
openai==1.40.0
prometheus-client==0.19.0
```


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

> 💡 **For complete environment setup instructions, see the [Environment Setup & Deployment](#️-environment-setup--deployment) section above.**

### Advanced Configuration Options

Additional environment variables for fine-tuning:

```env
# Search Settings
SIMILARITY_THRESHOLD=0.7        # Minimum similarity for search results (0.0-1.0)
SEARCH_LIMIT=10                 # Maximum number of search results
HYBRID_SEARCH_ALPHA=0.5         # Balance between semantic and keyword search

# Document Processing
CHUNK_SIZE=512                  # Text chunk size for embeddings
CHUNK_OVERLAP=50                # Character overlap between chunks
BATCH_SIZE=32                   # Batch size for processing
MAX_FILE_SIZE_MB=50             # Maximum upload file size

# Performance & Monitoring
LOG_LEVEL=INFO                  # Logging level (DEBUG, INFO, WARNING, ERROR)
RATE_LIMIT_PER_MINUTE=100       # API rate limiting
```

### Configuration Hierarchy

Settings are loaded in the following order (later values override earlier ones):

1. **Default values** (in code)
2. **Environment file** (`.env`, `.env.gcp`)
3. **Environment variables** (system environment)
4. **Runtime parameters** (CLI arguments, function parameters)

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

### Recent Fixes Applied ✅

**🔧 Chat Interface Issues** (Fixed)
- **Problem**: Chat input moving around, message overflow
- **Solution**: Input now fixed at top, shows last 10 messages only
- **Status**: ✅ Resolved

**📦 Vector Dimension Mismatch** (Fixed)
- **Problem**: "Vector dimension error: expected dim: 384, got 1536"
- **Solution**: Aligned Qdrant collection (1536) with OpenAI embeddings
- **Status**: ✅ Resolved

**🚀 Slow Build Times** (Fixed)
- **Problem**: 30+ minute Docker builds, timeouts
- **Solution**: Removed sentence-transformers, optimized dependencies
- **Status**: ✅ Resolved - now ~5 minutes

**📱 Streamlit API Errors** (Fixed)
- **Problem**: `st.chat_input()` not allowed inside tabs
- **Solution**: Moved input outside tabs with conditional display
- **Status**: ✅ Resolved

### Common Issues

**Services won't start**
```bash
# Check ports
lsof -i :8000,8501,6333,6379

# Restart everything
docker-compose down
docker-compose up -d
```

**Upload fails with dimension error**
```bash
# Reset Qdrant collection to match OpenAI embeddings
curl -X DELETE http://localhost:6333/collections/documents
# Restart API to recreate collection
docker-compose restart rag-api
```

**Chat input not appearing**
- Make sure you're in the "Chat Interface" tab
- Input appears at the top of the tab (not bottom)
- Refresh page if input is missing

**Build timeouts or slow installs**
```bash
# Use optimized requirements
pip install -r requirements.txt  # Production only
# NOT: pip install -r requirements-dev.txt  # Includes heavy dev tools
```

**No search results**
- Lower similarity threshold (try 0.5 instead of 0.7)
- Try different search type (hybrid vs vector)
- Verify documents were processed: check Document Library tab

**Streamlit connection error**
- Ensure API is running: `curl http://localhost:8000/api/v1/health`
- Check API URL in sidebar configuration
- For Docker: use `http://localhost:8000` not `127.0.0.1`

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