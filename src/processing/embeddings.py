from typing import List, Dict, Any, Union
import numpy as np
from tenacity import retry, stop_after_attempt, wait_exponential
import asyncio
from concurrent.futures import ThreadPoolExecutor
from src.config import settings
from src.monitoring.logger import get_logger
from src.monitoring.metrics import track_embedding_generation
import time

logger = get_logger(__name__)


class EmbeddingGenerator:
    """Generate embeddings for text chunks."""
    
    def __init__(self):
        self.model_name = settings.embedding_model
        self.batch_size = settings.batch_size
        self._model = None
        self._executor = ThreadPoolExecutor(max_workers=4)
    
    @property
    def model(self):
        """Lazy load the embedding model."""
        if self._model is None:
            logger.info("loading_embedding_model", model=self.model_name)
            
            if "sentence-transformers" in self.model_name:
                try:
                    from sentence_transformers import SentenceTransformer
                    self._model = SentenceTransformer(self.model_name.split("/")[-1])
                    logger.info("embedding_model_loaded", model=self.model_name)
                except ImportError:
                    logger.error("sentence_transformers_not_installed")
                    # Fallback to OpenAI
                    self.model_name = "text-embedding-ada-002"
                    self._model = "openai"
            else:
                self._model = "openai"
        
        return self._model
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def generate_embeddings(
        self, 
        texts: List[str], 
        metadata: List[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Generate embeddings for a list of texts."""
        start_time = time.time()
        
        try:
            if not texts:
                return []
            
            # Generate embeddings based on model type
            if self._model == "openai" or self.model == "openai":
                embeddings = await self._generate_openai_embeddings(texts)
            else:
                embeddings = await self._generate_sentence_transformer_embeddings(texts)
            
            # Combine with metadata
            results = []
            for i, (text, embedding) in enumerate(zip(texts, embeddings)):
                result = {
                    "text": text,
                    "embedding": embedding,
                    "metadata": metadata[i] if metadata and i < len(metadata) else {}
                }
                results.append(result)
            
            duration = time.time() - start_time
            track_embedding_generation(duration)
            
            logger.info(
                "embeddings_generated",
                count=len(results),
                model=self.model_name,
                duration=duration
            )
            
            return results
            
        except Exception as e:
            logger.error("embedding_generation_failed", error=str(e))
            raise
    
    async def _generate_openai_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using OpenAI API."""
        try:
            import openai
            from openai import AsyncOpenAI
            
            client = AsyncOpenAI(api_key=settings.openai_api_key)
            
            embeddings = []
            
            # Process in batches
            for i in range(0, len(texts), self.batch_size):
                batch = texts[i:i + self.batch_size]
                
                response = await client.embeddings.create(
                    model="text-embedding-ada-002",
                    input=batch
                )
                
                batch_embeddings = [item.embedding for item in response.data]
                embeddings.extend(batch_embeddings)
            
            return embeddings
            
        except Exception as e:
            logger.error("openai_embedding_failed", error=str(e))
            raise
    
    async def _generate_sentence_transformer_embeddings(
        self, 
        texts: List[str]
    ) -> List[List[float]]:
        """Generate embeddings using sentence-transformers."""
        loop = asyncio.get_event_loop()
        
        # Run CPU-intensive embedding generation in thread pool
        embeddings = await loop.run_in_executor(
            self._executor,
            self._generate_embeddings_sync,
            texts
        )
        
        return embeddings.tolist()
    
    def _generate_embeddings_sync(self, texts: List[str]) -> np.ndarray:
        """Synchronous embedding generation for sentence-transformers."""
        return self.model.encode(
            texts,
            batch_size=self.batch_size,
            show_progress_bar=False,
            convert_to_numpy=True
        )
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings."""
        if self._model == "openai" or self.model == "openai":
            return 1536  # OpenAI ada-002 dimension
        else:
            return self.model.get_sentence_embedding_dimension()


class EmbeddingCache:
    """Simple in-memory cache for embeddings."""
    
    def __init__(self, max_size: int = 1000):
        self.cache: Dict[str, List[float]] = {}
        self.max_size = max_size
    
    def get(self, text: str) -> Union[List[float], None]:
        """Get embedding from cache."""
        return self.cache.get(self._hash_text(text))
    
    def set(self, text: str, embedding: List[float]) -> None:
        """Store embedding in cache."""
        if len(self.cache) >= self.max_size:
            # Remove oldest entry (simple FIFO)
            self.cache.pop(next(iter(self.cache)))
        
        self.cache[self._hash_text(text)] = embedding
    
    def _hash_text(self, text: str) -> str:
        """Create a hash of text for cache key."""
        import hashlib
        return hashlib.md5(text.encode()).hexdigest()