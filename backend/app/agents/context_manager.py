from typing import List, Dict, Any
from app.core.logging_config import logger

class ContextManager:
    """
    Context Manager compiles short-term dialogue context and long-term Qdrant vector memory 
    into a formatted payload for LLM injection.
    """
    
    async def assemble_context(self, session_id: str, query: str, memory_manager: Any) -> str:
        """
        Retrieves and formats short-term history and semantic long-term memories.
        """
        logger.info(f"Assembling context for query in session {session_id}")
        
        # 1. Retrieve short-term dialogue history
        history = await memory_manager.get_short_term_memory(session_id)
        formatted_history = []
        for msg in history:
            role_label = "User" if msg["role"] == "user" else "Assistant"
            if msg["role"] != "system":
                formatted_history.append(f"{role_label}: {msg['content']}")
        
        history_text = "\n".join(formatted_history[-6:])  # Limit context window to last 6 dialogue segments
        
        # 2. Retrieve long-term memories via vector database
        memories = await memory_manager.search_long_term_memory(query, limit=3)
        formatted_memories = []
        for hit in memories:
            payload = hit.get("payload", {})
            fact = payload.get("fact")
            if fact:
                formatted_memories.append(f"- {fact}")
                
        memories_text = "\n".join(formatted_memories) if formatted_memories else "No past records found."
        
        context_payload = (
            f"=== LONG-TERM USER PROFILE FACTS ===\n{memories_text}\n\n"
            f"=== RECENT CONVERSATION HISTORY ===\n{history_text}"
        )
        return context_payload
