from typing import List, Dict, Any, Optional, Tuple
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, 
    Filter, FieldCondition, MatchValue
)
import uuid
from datetime import datetime
from src.config import settings
from src.monitoring.logger import get_logger
from src.monitoring.metrics import track_vector_search, vector_db_size
import time

logger = get_logger(__name__)


class VectorStore:
    """Qdrant vector database interface."""
    
    def __init__(self):
        self.client = QdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port
        )
        self.collection_name = settings.qdrant_collection
        self._ensure_collection()
    
    def _ensure_collection(self):
        """Ensure the collection exists with proper configuration."""
        try:
            collections = self.client.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)
            
            if not exists:
                logger.info("creating_collection", collection=self.collection_name)
                
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=settings.embedding_dimension,
                        distance=Distance.COSINE
                    )
                )
                
                # Create payload indices for filtering
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name="document_id",
                    field_schema="keyword"
                )
                
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name="document_type",
                    field_schema="keyword"
                )
                
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name="timestamp",
                    field_schema="integer"
                )
                
                logger.info("collection_created", collection=self.collection_name)
            else:
                logger.info("collection_exists", collection=self.collection_name)
                
        except Exception as e:
            logger.error("collection_setup_failed", error=str(e))
            raise
    
    async def upsert_documents(
        self, 
        documents: List[Dict[str, Any]]
    ) -> List[str]:
        """Insert or update documents with embeddings."""
        if not documents:
            return []
        
        points = []
        document_ids = []
        
        for doc in documents:
            point_id = str(uuid.uuid4())
            document_id = doc.get("metadata", {}).get("document_id", point_id)
            
            # Prepare payload
            payload = {
                "text": doc["text"],
                "document_id": document_id,
                "chunk_id": doc.get("chunk_id", 0),
                "document_type": doc.get("metadata", {}).get("document_type", "unknown"),
                "timestamp": int(datetime.now().timestamp()),
                **doc.get("metadata", {})
            }
            
            point = PointStruct(
                id=point_id,
                vector=doc["embedding"],
                payload=payload
            )
            
            points.append(point)
            document_ids.append(document_id)
        
        # Batch upsert
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )
        
        # Update metrics
        count = self.client.count(collection_name=self.collection_name).count
        vector_db_size.set(count)
        
        logger.info(
            "documents_upserted",
            count=len(points),
            collection=self.collection_name,
            total_documents=count
        )
        
        return document_ids
    
    async def search(
        self,
        query_embedding: List[float],
        limit: int = None,
        filters: Dict[str, Any] = None,
        similarity_threshold: float = None
    ) -> List[Dict[str, Any]]:
        """Search for similar documents using vector similarity."""
        start_time = time.time()
        
        limit = limit or settings.search_limit
        similarity_threshold = similarity_threshold or settings.similarity_threshold
        
        # Build filter conditions
        filter_conditions = []
        if filters:
            for field, value in filters.items():
                if value is not None:
                    filter_conditions.append(
                        FieldCondition(
                            key=field,
                            match=MatchValue(value=value)
                        )
                    )
        
        # Perform search
        search_filter = Filter(must=filter_conditions) if filter_conditions else None
        
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=limit,
            query_filter=search_filter,
            score_threshold=similarity_threshold
        )
        
        # Format results
        formatted_results = []
        for result in results:
            formatted_results.append({
                "id": result.id,
                "score": result.score,
                "text": result.payload.get("text", ""),
                "metadata": {
                    k: v for k, v in result.payload.items() 
                    if k != "text"
                }
            })
        
        duration = time.time() - start_time
        track_vector_search(search_type="vector", duration=duration)
        
        logger.info(
            "vector_search_completed",
            results_count=len(formatted_results),
            limit=limit,
            threshold=similarity_threshold,
            duration=duration
        )
        
        return formatted_results
    
    async def hybrid_search(
        self,
        query_embedding: List[float],
        query_text: str,
        limit: int = None,
        filters: Dict[str, Any] = None,
        similarity_threshold: float = None,
        alpha: float = None
    ) -> List[Dict[str, Any]]:
        """Perform hybrid search combining vector and keyword search."""
        start_time = time.time()
        
        alpha = alpha or settings.hybrid_search_alpha
        
        # Get vector search results
        vector_results = await self.search(
            query_embedding=query_embedding,
            limit=limit * 2,  # Get more results for re-ranking
            filters=filters,
            similarity_threshold=similarity_threshold
        )
        
        # Improved keyword matching with partial matches
        query_terms = query_text.lower().split()
        
        # Score and combine results
        hybrid_results = []
        for result in vector_results:
            text = result["text"].lower()
            
            # Calculate keyword score with partial matching
            keyword_score = 0
            if query_terms:
                matches = 0
                for term in query_terms:
                    # Check for partial matches (substring matching)
                    if term in text:
                        matches += 1
                keyword_score = matches / len(query_terms)
            
            # Combine scores
            vector_score = result["score"]
            combined_score = alpha * vector_score + (1 - alpha) * keyword_score
            
            result["vector_score"] = vector_score
            result["keyword_score"] = keyword_score
            result["score"] = combined_score
            
            hybrid_results.append(result)
        
        # Sort by combined score and limit
        hybrid_results.sort(key=lambda x: x["score"], reverse=True)
        hybrid_results = hybrid_results[:limit or settings.search_limit]
        
        duration = time.time() - start_time
        track_vector_search(search_type="hybrid", duration=duration)
        
        logger.info(
            "hybrid_search_completed",
            results_count=len(hybrid_results),
            alpha=alpha,
            duration=duration
        )
        
        return hybrid_results
    
    async def delete_document(self, document_id: str) -> bool:
        """Delete all chunks of a document."""
        try:
            # Delete by document_id filter
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="document_id",
                            match=MatchValue(value=document_id)
                        )
                    ]
                )
            )
            
            # Update metrics
            count = self.client.count(collection_name=self.collection_name).count
            vector_db_size.set(count)
            
            logger.info(
                "document_deleted",
                document_id=document_id,
                remaining_documents=count
            )
            
            return True
            
        except Exception as e:
            logger.error("document_deletion_failed", document_id=document_id, error=str(e))
            return False
    
    async def list_documents(
        self, 
        offset: int = 0, 
        limit: int = 100
    ) -> Tuple[List[Dict[str, Any]], int]:
        """List all unique documents with metadata."""
        # Get all points (inefficient for large collections, but works for demo)
        all_points = self.client.scroll(
            collection_name=self.collection_name,
            limit=1000,  # Adjust based on expected collection size
            with_payload=True,
            with_vectors=False
        )[0]
        
        # Group by document_id
        documents = {}
        for point in all_points:
            doc_id = point.payload.get("document_id")
            if doc_id and doc_id not in documents:
                documents[doc_id] = {
                    "document_id": doc_id,
                    "document_type": point.payload.get("document_type", "unknown"),
                    "filename": point.payload.get("filename", ""),
                    "timestamp": point.payload.get("timestamp"),
                    "chunk_count": 0
                }
            if doc_id:
                documents[doc_id]["chunk_count"] += 1
        
        # Convert to list and paginate
        doc_list = list(documents.values())
        total = len(doc_list)
        
        # Sort by timestamp (newest first)
        doc_list.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
        
        # Paginate
        paginated = doc_list[offset:offset + limit]
        
        return paginated, total