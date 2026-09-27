import json
import re
from typing import Dict, Any, Optional
from app.llm.gateway import LLMGateway
from app.agents.planner_agent import PlanStep
from app.config.prompts import REASONING_PROMPT, REFLECTION_PROMPT, SYSTEM_PROMPT
from app.core.logging_config import logger

class ReasoningEngine:
    """
    Formulates arguments for tool calls and performs self-reflection and correction checks on execution outputs.
    """
    def __init__(self, llm_gateway: Optional[LLMGateway] = None):
        self.llm = llm_gateway or LLMGateway()

    async def formulate_arguments(
        self, 
        goal: str, 
        step: PlanStep, 
        tool_schema: Dict[str, Any], 
        plan_trace: str, 
        context_text: str
    ) -> Dict[str, Any]:
        """
        Interacts with the LLM using REASONING_PROMPT to output exact JSON arguments matching a tool's schema.
        """
        logger.info(f"Formulating parameters for tool '{step.tool_name}' on step {step.id}")
        
        prompt = REASONING_PROMPT.format(
            goal=goal,
            task_desc=f"{step.task}: {step.description}",
            tool_schema=json.dumps(tool_schema, indent=2),
            plan_trace=plan_trace,
            context_text=context_text
        )

        try:
            raw_response = await self.llm.generate([
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ], temperature=0.1)

            cleaned = self._extract_json_block(raw_response)
            if not cleaned or cleaned.strip() == "{}":
                return {}
            
            args = json.loads(cleaned)
            logger.info(f"Formulated parameters: {args}")
            return args
        except Exception as e:
            logger.error(f"Error formulating tool parameters for step {step.id}: {e}")
            return {}

    async def reflect_on_outcome(
        self, 
        goal: str, 
        step: PlanStep, 
        tool_args: Dict[str, Any], 
        tool_output: str
    ) -> Dict[str, Any]:
        """
        Evaluates raw tool responses using REFLECTION_PROMPT to confirm success or flag errors/corrections.
        """
        logger.info(f"Reflecting on outcome for step {step.id}...")
        
        prompt = REFLECTION_PROMPT.format(
            goal=goal,
            task_desc=f"{step.task}: {step.description}",
            tool_args=json.dumps(tool_args),
            tool_output=tool_output
        )

        try:
            raw_response = await self.llm.generate([
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ], temperature=0.1)

            cleaned = self._extract_json_block(raw_response)
            reflection = json.loads(cleaned)
            logger.info(f"Reflection outcome: {reflection.get('status')} | Correction needed: {reflection.get('correction_required')}")
            return reflection
        except Exception as e:
            logger.error(f"Reflection parsing error: {e}")
            # Safe default fallback assuming success unless flagged as fatal error
            return {
                "status": "completed",
                "thought": "Reflection parser failed, defaulted to completed.",
                "correction_required": False,
                "correction_details": None
            }

    def _extract_json_block(self, text: str) -> str:
        text_stripped = text.strip()
        match = re.search(r"({.*})", text_stripped, re.DOTALL)
        if match:
            return match.group(1)
        return text_stripped
