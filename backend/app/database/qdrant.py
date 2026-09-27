import os
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models
from app.config.settings import settings
from app.core.logging_config import logger
from app.core.errors import DatabaseError

class QdrantVectorDB:
    def __init__(self):
        self.client: Optional[QdrantClient] = None
        self.initialize_client()

    def initialize_client(self) -> None:
        """Initializes the Qdrant client with config credentials."""
        try:
            if settings.QDRANT_URL:
                if settings.QDRANT_URL == ":memory:":
                    self.client = QdrantClient(location=":memory:")
                else:
                    self.client = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY)
            else:
                try:
                    # Attempt connecting to external/docker Qdrant instance
                    test_client = QdrantClient(
                        host=settings.QDRANT_HOST,
                        port=settings.QDRANT_PORT,
                        api_key=settings.QDRANT_API_KEY,
                        timeout=1.5
                    )
                    test_client.get_collections()
                    self.client = test_client
                except Exception:
                    # Fallback to localized on-disk storage directory for standalone laptop mode
                    local_dir = os.path.join(
                        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                        "qdrant_storage"
                    )
                    os.makedirs(local_dir, exist_ok=True)
                    logger.info(f"External Qdrant service not reachable. Running embedded vector store at: {local_dir}")
                    self.client = QdrantClient(path=local_dir)
            logger.info("Qdrant client initialized successfully")
        except Exception as e:
            logger.warning(f"Could not connect to Qdrant vector database: {e}. Qdrant operations will fail.")
            self.client = None

    def ensure_collection_exists(self, collection_name: str, vector_size: int = 1536) -> None:
        """
        Creates a collection in Qdrant if it does not already exist.
        Default vector size is 1536 (OpenAI text-embedding-3-small / text-embedding-ada-002).
        """
        if not self.client:
            logger.warning("Qdrant client is not available. Skipping collection verification.")
            return

        try:
            collections = self.client.get_collections().collections
            collection_names = [col.name for col in collections]
            
            if collection_name not in collection_names:
                logger.info(f"Creating collection {collection_name} in Qdrant...")
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=models.VectorParams(
                        size=vector_size,
                        distance=models.Distance.COSINE
                    )
                )
                logger.info(f"Collection {collection_name} created successfully.")
        except Exception as e:
            logger.error(f"Error checking/creating Qdrant collection: {e}")
            raise DatabaseError("Failed to verify Qdrant collection", detail=str(e))

    async def upsert_vector(
        self, 
        collection_name: str, 
        vector: List[float], 
        payload: Dict[str, Any], 
        point_id: str
    ) -> None:
        """
        Saves a vector embedding along with metadata payload to Qdrant.
        """
        if not self.client:
            raise DatabaseError("Qdrant client is not initialized")

        try:
            # Running synchronous Qdrant Client method in a wrapper if needed, 
            # but standard client is simple synchronous.
            self.client.upsert(
                collection_name=collection_name,
                points=[
                    models.PointStruct(
                        id=point_id,
                        vector=vector,
                        payload=payload
                    )
                ]
            )
            logger.debug(f"Successfully upserted point {point_id} to Qdrant collection {collection_name}")
        except Exception as e:
            logger.error(f"Qdrant upsert failed for point {point_id}: {e}")
            raise DatabaseError(f"Vector upsert failed: {str(e)}")

    async def search_similar(
        self, 
        collection_name: str, 
        query_vector: List[float], 
        limit: int = 5,
        score_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Searches the vector database for the most similar points.
        """
        if not self.client:
            raise DatabaseError("Qdrant client is not initialized")

        try:
            if hasattr(self.client, "query_points"):
                query_res = self.client.query_points(
                    collection_name=collection_name,
                    query=query_vector,
                    limit=limit,
                    score_threshold=score_threshold
                )
                results = query_res.points
            else:
                results = self.client.search(
                    collection_name=collection_name,
                    query_vector=query_vector,
                    limit=limit,
                    score_threshold=score_threshold
                )
            
            return [
                {
                    "id": hit.id,
                    "score": hit.score,
                    "payload": hit.payload
                }
                for hit in results
            ]
        except Exception as e:
            logger.error(f"Qdrant search failed in collection {collection_name}: {e}")
            raise DatabaseError(f"Vector similarity search failed: {str(e)}")

qdrant_db = QdrantVectorDB()
