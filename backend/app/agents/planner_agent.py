import json
import re
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from app.llm.gateway import LLMGateway
from app.config.prompts import PLANNER_PROMPT, SYSTEM_PROMPT
from app.core.logging_config import logger
from app.core.errors import AgentExecutionError
from app.agents.tool_selector import ToolSelector

class PlanStep(BaseModel):
    id: int
    task: str
    description: str
    tool_name: Optional[str] = None
    dependencies: List[int] = []
    status: str = "pending"  # "pending", "running", "completed", "failed"
    result: Optional[str] = None

class ExecutionPlan(BaseModel):
    goal: str
    steps: List[PlanStep]

class PlannerAgent:
    """
    Decomposes the user request into sequential task steps with dependencies and MCP tools using the LLM.
    """
    def __init__(self, llm_gateway: Optional[LLMGateway] = None):
        self.llm = llm_gateway or LLMGateway()
        self.tool_selector = ToolSelector(self.llm)

    async def generate_plan(
        self, 
        user_request: str, 
        available_tools: List[Dict[str, Any]], 
        context_text: str
    ) -> ExecutionPlan:
        """
        Interacts with the LLM to generate an execution plan for a user query.
        """
        logger.info(f"Generating execution plan for user request: '{user_request[:50]}'")

        # 1. Prepare tool details for LLM
        tools_summary = [
            {
                "name": t.get("name"),
                "description": t.get("description"),
                "input_schema": t.get("input_schema")
            }
            for t in available_tools
        ]
        tools_json = json.dumps(tools_summary, indent=2)

        # 2. Formulate the prompt
        prompt = PLANNER_PROMPT.format(
            goal=user_request,
            tools_json=tools_json,
            context_text=context_text
        )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]

        # 3. Call LLM
        try:
            raw_response = await self.llm.generate(messages, temperature=0.2)
            
            # Clean up response to extract JSON block (e.g. if code fenced)
            cleaned_response = self._clean_json_response(raw_response)
            
            plan_dict = json.loads(cleaned_response)
            
            # 4. Map steps and validate tools
            steps_list = []
            for step_data in plan_dict.get("steps", []):
                tool_name = step_data.get("tool_name")
                
                # Double-check and validate tool assignment via tool selector
                if tool_name:
                    valid_tool = await self.tool_selector.match_task_to_tool(
                        step_data.get("task") + " - " + step_data.get("description"),
                        available_tools
                    )
                    if valid_tool:
                        tool_name = valid_tool
                    else:
                        logger.warning(f"Planner suggested tool '{tool_name}' but it is not available or valid. Defaulting to local reasoning.")
                        tool_name = None

                step = PlanStep(
                    id=int(step_data.get("id")),
                    task=step_data.get("task"),
                    description=step_data.get("description"),
                    tool_name=tool_name,
                    dependencies=step_data.get("dependencies", []),
                    status="pending"
                )
                steps_list.append(step)

            logger.info(f"Execution plan created successfully. Total steps: {len(steps_list)}")
            return ExecutionPlan(
                goal=user_request,
                steps=steps_list
            )

        except Exception as e:
            logger.error(f"Failed to generate/parse planner execution plan: {e}", exc_info=True)
            raise AgentExecutionError("Failed to build execution plan", detail=str(e))

    def _clean_json_response(self, response: str) -> str:
        """
        Strips markdown code fences (e.g. ```json ... ```) to isolate raw JSON.
        """
        response_stripped = response.strip()
        # Find JSON boundaries
        match = re.search(r"({.*})", response_stripped, re.DOTALL)
        if match:
            return match.group(1)
        return response_stripped
