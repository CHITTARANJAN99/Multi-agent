from typing import Optional, List, Dict
from app.llm.gateway import LLMGateway
from app.config.prompts import SUMMARIZATION_PROMPT, SYSTEM_PROMPT
from app.core.logging_config import logger

class ResponseGenerator:
    """
    Synthesizes the final markdown user response based on completed step traces.
    """
    def __init__(self, llm_gateway: Optional[LLMGateway] = None):
        self.llm = llm_gateway or LLMGateway()

    async def generate_final_response(self, goal: str, plan_trace: str) -> str:
        """
        Uses LLM to summarize outputs and present the completed execution path answers.
        """
        logger.info("Generating final consolidated response...")
        prompt = SUMMARIZATION_PROMPT.format(
            goal=goal,
            plan_trace=plan_trace
        )
        try:
            return await self.llm.generate([
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ], temperature=0.5)
        except Exception as e:
            logger.critical(f"Failed to generate final response: {e}")
            return f"The request completed, but final response formatting failed. Summary details: {plan_trace}"
