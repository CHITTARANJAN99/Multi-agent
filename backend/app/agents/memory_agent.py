import json
import re
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from app.llm.gateway import LLMGateway
from app.config.prompts import MEMORY_EXTRACTION_PROMPT, SYSTEM_PROMPT
from app.core.logging_config import logger

class ExtractedMemory(BaseModel):
    fact: str
    category: str  # e.g., "user_preference", "project_details", "general_fact"
    importance: int  # 1 to 5
    keywords: List[str]

class MemoryAgent:
    """
    Extracts user facts, details, and preferences from dialogue histories.
    """
    def __init__(self, llm_gateway: Optional[LLMGateway] = None):
        self.llm = llm_gateway or LLMGateway()

    async def extract_memories(self, conversation_history: List[Dict[str, str]]) -> List[ExtractedMemory]:
        """
        Uses LLM with MEMORY_EXTRACTION_PROMPT to output structured persistent facts.
        """
        logger.info(f"Extracting memories from conversation of length {len(conversation_history)}")
        
        if not conversation_history or len(conversation_history) < 2:
            return []

        # 1. Format the conversation transcript
        dialogue_turns = []
        for turn in conversation_history:
            role = "User" if turn["role"] == "user" else "Assistant"
            if turn["role"] != "system":
                dialogue_turns.append(f"{role}: {turn['content']}")
        
        conversation_text = "\n".join(dialogue_turns)

        # 2. Formulate prompt
        prompt = MEMORY_EXTRACTION_PROMPT.format(conversation_text=conversation_text)

        try:
            raw_response = await self.llm.generate([
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ], temperature=0.1)

            # Strip markdown braces if any
            cleaned = self._clean_json_response(raw_response)
            
            memories_list = json.loads(cleaned)
            extracted = []
            
            for item in memories_list:
                extracted.append(
                    ExtractedMemory(
                        fact=item.get("fact"),
                        category=item.get("category", "general_fact"),
                        importance=int(item.get("importance", 3)),
                        keywords=item.get("keywords", [])
                    )
                )
            
            logger.info(f"Successfully extracted {len(extracted)} persistent facts/memories.")
            return extracted

        except Exception as e:
            logger.error(f"Failed to parse or extract memories: {e}")
            return []

    def _clean_json_response(self, response: str) -> str:
        response_stripped = response.strip()
        match = re.search(r"(\[.*\])", response_stripped, re.DOTALL)
        if match:
            return match.group(1)
        return response_stripped
