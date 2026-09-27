import json
from typing import List, Dict, Any, Optional
from app.llm.gateway import LLMGateway
from app.core.logging_config import logger

class ToolSelector:
    """
    Analyzes task descriptions and maps them to discovered MCP tools.
    """
    def __init__(self, llm_gateway: Optional[LLMGateway] = None):
        self.llm = llm_gateway or LLMGateway()

    async def match_task_to_tool(self, task_description: str, available_tools: List[Dict[str, Any]]) -> Optional[str]:
        """
        Queries the LLM or performs semantic mapping to select the best MCP tool for a subtask.
        """
        if not available_tools:
            return None

        # 1. Simple heuristic match first to optimize speed
        desc_lower = task_description.lower()
        for tool in available_tools:
            name = tool.get("name", "").lower()
            desc = tool.get("description", "").lower()
            # If the tool name or description matches keywords exactly, map it
            if name in desc_lower or (len(name) > 3 and name.replace("_", " ").replace("-", " ") in desc_lower):
                logger.info(f"Heuristic matched task '{task_description[:30]}' to tool '{tool.get('name')}'")
                return tool.get("name")

        # 2. LLM-driven selector fallback
        logger.info(f"Using LLM to select tool for task: '{task_description[:50]}'")
        
        tools_summary = [
            {"name": t.get("name"), "description": t.get("description")} 
            for t in available_tools
        ]
        
        prompt = (
            "Given a subtask description and a list of available tools, choose the best tool to resolve the subtask. "
            "If no tool fits the subtask, return 'none'.\n\n"
            f"Subtask: \"{task_description}\"\n"
            f"Available Tools: {json.dumps(tools_summary)}\n\n"
            "Return ONLY the tool name (lowercase, matching the list) or the word 'none'. Do not include formatting or markdown."
        )

        try:
            response = await self.llm.generate([
                {"role": "user", "content": prompt}
            ], temperature=0.1)
            
            selected = response.strip().lower()
            if selected == "none" or not any(t.get("name") == selected for t in available_tools):
                logger.debug(f"LLM decided no tool fits for: '{task_description[:30]}'")
                return None
            
            logger.info(f"LLM matched task to tool: '{selected}'")
            return selected
        except Exception as e:
            logger.error(f"Error matching tool via LLM: {e}")
            return None
