from typing import AsyncGenerator, Dict, Any, Optional

from app.core.logging_config import logger
from app.llm.gateway import LLMGateway
from app.memory.manager import MemoryManager
from app.agents.workflow_executor import WorkflowExecutor

class WorkflowOrchestrator:
    """
    Facade routing dialogue requests to the modular AI Reasoning Layer WorkflowExecutor.
    """
    def __init__(
        self, 
        llm_gateway: Optional[LLMGateway] = None,
        memory_manager: Optional[MemoryManager] = None
    ):
        self.llm = llm_gateway or LLMGateway()
        self.memory = memory_manager or MemoryManager(llm_gateway=self.llm)
        self.executor = WorkflowExecutor(self.llm)

    async def execute(
        self, 
        user_request: str, 
        session_id: str
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Delegates plan generation, task scheduling, reasoning and execution loops.
        """
        logger.info(f"Delegating chat workflow to reasoning engine executor: session_id={session_id}")
        
        async for event in self.executor.execute_workflow(
            user_request=user_request,
            session_id=session_id,
            memory_manager=self.memory
        ):
            yield event

    async def resume(
        self,
        session_id: str,
        step_id: int,
        approved: bool
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Delegates resumption of a suspended workflow execution.
        """
        logger.info(f"Resuming chat workflow: session_id={session_id}, step_id={step_id}")
        
        async for event in self.executor.resume_workflow(
            session_id=session_id,
            step_id=step_id,
            approved=approved,
            memory_manager=self.memory
        ):
            yield event

orchestrator = WorkflowOrchestrator()

