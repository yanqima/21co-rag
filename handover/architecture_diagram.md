# System Architecture Diagram

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Client Applications                            │
│  (Web Browser, Mobile App, API Clients, Streamlit UI)                  │
└─────────────────────────┬───────────────────────────────────────────────┘
                          │ HTTPS
                          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        Load Balancer (ALB/Nginx)                        │
│                     (SSL Termination, Rate Limiting)                    │
└─────────────────────────┬───────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          FastAPI Application                            │
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────────────┐   │
│  │   Middleware    │  │   API Routes     │  │   Background Jobs  │   │
│  │ - CORS         │  │ - /ingest        │  │ - Doc Processing   │   │
│  │ - Rate Limit   │  │ - /query         │  │ - Embedding Gen    │   │
│  │ - Logging      │  │ - /documents     │  │ - Async Tasks      │   │
│  │ - Metrics      │  │ - /health        │  └────────┬───────────┘   │
│  └─────────────────┘  └──────────────────┘           │               │
└─────────────────────────┬─────────────────────────────┼───────────────┘
                          │                             │
                          ▼                             ▼
┌─────────────────────────────────────┐  ┌─────────────────────────────┐
│         Vector Database              │  │      Message Queue           │
│           (Qdrant)                   │  │        (Redis)              │
│  ┌─────────────────────────────┐   │  │  ┌────────────────────────┐ │
│  │   Document Embeddings        │   │  │  │  Processing Jobs       │ │
│  │   - 1536-dim vectors         │   │  │  │  - Document Queue      │ │
│  │   - Metadata indices         │   │  │  │  - Progress Tracking    │ │
│  │   - Hybrid Search            │   │  │  │  - Job Status          │ │
│  └─────────────────────────────┘   │  │  └────────────────────────┘ │
└─────────────────────────────────────┘  └─────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        External Services                                │
│  ┌─────────────────────┐        ┌─────────────────────────────────┐   │
│  │   OpenAI API        │        │     Monitoring Stack            │   │
│  │ - Embeddings        │        │   - Prometheus (Metrics)        │   │
│  │ - Chat Completions  │        │   - Grafana (Visualization)     │   │
│  └─────────────────────┘        │   - CloudWatch (Logs)           │   │
│                                  └─────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

## Data Flow Diagram

```
Document Ingestion Flow:
========================

Client                API                  Redis              Qdrant          OpenAI
  │                    │                    │                   │               │
  ├──Upload File──────►│                    │                   │               │
  │                    ├──Validate──────────┤                   │               │
  │                    ├──Queue Job─────────►                   │               │
  │◄──Job ID───────────┤                    │                   │               │
  │                    │                    │                   │               │
  │              [Background Worker]        │                   │               │
  │                    ├──Get Job◄──────────┤                   │               │
  │                    ├──Extract Text──────┤                   │               │
  │                    ├──Chunk Text────────┤                   │               │
  │                    ├──Generate Embeddings───────────────────┼──────────────►│
  │                    │◄───────────────────────────────────────┼──Embeddings───┤
  │                    ├──Store Vectors─────┼──────────────────►│               │
  │                    ├──Update Status─────►                   │               │
  │                    │                    │                   │               │


Query Flow:
===========

Client                API                  Qdrant              OpenAI
  │                    │                    │                    │
  ├──Search Query─────►│                    │                    │
  │                    ├──Generate Embedding┼───────────────────►│
  │                    │◄───────────────────┼────Embedding───────┤
  │                    ├──Hybrid Search────►│                    │
  │                    │◄──Results──────────┤                    │
  │                    ├──Generate Answer───┼───────────────────►│
  │                    │◄───────────────────┼────Response────────┤
  │◄──JSON Response────┤                    │                    │
  │                    │                    │                    │
```

## Component Details

### 1. API Layer (FastAPI)
- **Responsibility**: HTTP request handling, validation, routing
- **Key Features**: 
  - Async request processing
  - Automatic OpenAPI documentation
  - Request/response validation with Pydantic
  - Middleware for cross-cutting concerns

### 2. Document Processing Pipeline
- **Components**:
  - File validators (size, type, content)
  - Text extractors (PDF, TXT, JSON)
  - Chunking strategies (fixed, semantic, sliding)
  - Embedding generator (batch processing)

### 3. Vector Storage (Qdrant)
- **Features**:
  - High-performance vector similarity search
  - Metadata filtering
  - Hybrid search (vector + keyword)
  - Persistent storage with snapshots

### 4. Background Processing (Redis)
- **Use Cases**:
  - Async document processing queue
  - Progress tracking
  - Rate limiting state
  - Caching (future enhancement)

### 5. Monitoring Stack
- **Metrics**: Prometheus format at `/metrics`
- **Logging**: Structured JSON with correlation IDs
- **Tracing**: OpenTelemetry ready
- **Alerting**: Based on error rates and latencies

## Security Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Security Layers                           │
├─────────────────────────────────────────────────────────────┤
│  1. Network Security                                        │
│     - VPC isolation                                         │
│     - Security groups                                       │
│     - Private subnets for databases                       │
│                                                             │
│  2. Application Security                                    │
│     - Input validation                                      │
│     - Rate limiting                                        │
│     - CORS configuration                                   │
│     - File size limits                                     │
│                                                             │
│  3. Data Security                                          │
│     - Encryption in transit (TLS)                         │
│     - Encryption at rest (EBS/EFS)                        │
│     - Secure credential management                        │
│                                                             │
│  4. Access Control                                         │
│     - API authentication (future)                          │
│     - Role-based access (future)                          │
│     - Audit logging                                       │
└─────────────────────────────────────────────────────────────┘
```

## Scaling Strategy

### Horizontal Scaling
- **API Servers**: Stateless, scale based on CPU/memory
- **Vector DB**: Read replicas for query distribution
- **Redis**: Cluster mode for high availability

### Vertical Scaling
- **Embedding Generation**: GPU instances for faster processing
- **Vector Search**: Memory-optimized instances

### Auto-scaling Triggers
- CPU utilization > 70%
- Memory utilization > 80%
- Request queue depth > 100
- Response time p95 > 1s