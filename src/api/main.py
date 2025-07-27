from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from src.api.routes import router
from src.api.middleware import (
    CorrelationIDMiddleware,
    LoggingMiddleware,
    RateLimitMiddleware,
    ErrorHandlerMiddleware
)
from src.monitoring.logger import setup_logging, get_logger
from src.config import settings

# Setup logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("application_starting", environment=settings.environment)
    
    yield
    
    # Shutdown
    logger.info("application_stopping")


# Create FastAPI app
app = FastAPI(
    title="RAG API",
    description="Production-ready Retrieval-Augmented Generation system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add middleware (order matters - error handler should be outermost)
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(CorrelationIDMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "RAG API is running",
        "version": "1.0.0",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.environment == "development",
        workers=settings.api_workers if settings.environment == "production" else 1,
        log_level=settings.log_level.lower()
    )