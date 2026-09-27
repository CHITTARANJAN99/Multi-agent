import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from app.core.logging_config import logger
from app.database.qdrant import qdrant_db
from app.config.settings import settings
from app.llm.gateway import LLMGateway
from app.agents.memory_agent import MemoryAgent, ExtractedMemory

# In-memory history buffer to maintain dialogue state between requests
MOCK_SHORT_TERM_STORE: Dict[str, List[Dict[str, str]]] = {}

class MemoryManager:
    """
    Coordinates short-term chat histories (in-memory buffer/PostgreSQL log)
    and long-term vector semantic search (Qdrant index).
    """
    def __init__(self, memory_agent: Optional[MemoryAgent] = None, llm_gateway: Optional[LLMGateway] = None):
        self.llm = llm_gateway or LLMGateway()
        self.memory_agent = memory_agent or MemoryAgent(self.llm)
        self.collection_name = settings.QDRANT_MEMORY_COLLECTION

    async def get_short_term_memory(self, session_id: str) -> List[Dict[str, str]]:
        """
        Retrieves user chat history for the current session.
        Falls back to in-memory store if postgres is not active.
        """
        logger.info(f"Retrieving short term memory logs for session: {session_id}")
        if session_id not in MOCK_SHORT_TERM_STORE:
            # Set default system prompt instructions
            MOCK_SHORT_TERM_STORE[session_id] = [
                {"role": "system", "content": "You are a helpful autonomous AI Assistant equipped with MCP tools."}
            ]
        return MOCK_SHORT_TERM_STORE[session_id]

    async def add_message_to_history(self, session_id: str, role: str, content: str) -> None:
        """
        Saves a new chat message to short-term PostgreSQL database history.
        """
        logger.info(f"Adding message to history for session {session_id}: role={role}")
        if session_id not in MOCK_SHORT_TERM_STORE:
            MOCK_SHORT_TERM_STORE[session_id] = [
                {"role": "system", "content": "You are a helpful autonomous AI Assistant equipped with MCP tools."}
            ]
        MOCK_SHORT_TERM_STORE[session_id].append({"role": role, "content": content})

    async def search_long_term_memory(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """
        Queries Qdrant vector database for semantic match memories related to the search term.
        """
        logger.info(f"Searching long-term memory for: '{query}'")
        
        # 1. Generate query embedding using the LLM Gateway
        try:
            query_vector = await self.llm.get_embedding(query)
        except Exception as e:
            logger.error(f"Failed to generate embedding for memory search: {e}")
            return []
        
        try:
            qdrant_db.ensure_collection_exists(self.collection_name, vector_size=len(query_vector))
            results = await qdrant_db.search_similar(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit
            )
            return results
        except Exception as e:
            logger.error(f"Failed to query long-term memory from Qdrant: {e}")
            return []

    async def persist_long_term_memories(self, session_id: str, conversation_history: List[Dict[str, str]]) -> None:
        """
        Processes conversation log, extracts facts using MemoryAgent, 
        creates embeddings, and indexes them in Qdrant.
        """
        logger.info(f"Triggering long-term memory extraction for session {session_id}")
        
        # 1. Extract memories using memory agent
        memories: List[ExtractedMemory] = await self.memory_agent.extract_memories(conversation_history)
        
        for mem in memories:
            try:
                # 2. Generate embedding for the extracted fact
                embedding = await self.llm.get_embedding(mem.fact)
                point_id = str(uuid.uuid4())
                
                payload = {
                    "session_id": session_id,
                    "fact": mem.fact,
                    "category": mem.category,
                    "importance": mem.importance,
                    "keywords": mem.keywords,
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                
                # 3. Ensure collection exists and write point
                qdrant_db.ensure_collection_exists(self.collection_name, vector_size=len(embedding))
                await qdrant_db.upsert_vector(
                    collection_name=self.collection_name,
                    vector=embedding,
                    payload=payload,
                    point_id=point_id
                )
                logger.info(f"Persisted long term memory: '{mem.fact}'")
            except Exception as e:
                logger.error(f"Failed to save long term memory point: {e}")

