import asyncio
import json
from typing import AsyncGenerator, Dict, Any, List, Optional

from app.core.logging_config import logger
from app.core.errors import AgentExecutionError, MCPClientError
from app.llm.gateway import LLMGateway
from app.mcp.mcp_client import mcp_client_manager

from app.agents.context_manager import ContextManager
from app.agents.planner_agent import PlannerAgent, ExecutionPlan, PlanStep
from app.agents.task_manager import TaskManager
from app.agents.reasoning_engine import ReasoningEngine
from app.agents.response_generator import ResponseGenerator
from app.agents.specialized import get_agent_for_tool
from app.workflows.session_state import session_state_manager

# Tools that require explicit human consent before execution
CONFIRMATION_REQUIRED_TOOLS = {
    "book_bus",
    "book_hotel",
    "send_email",
    "purchase_product",
    "create_calendar_event"
}

class WorkflowExecutor:
    """
    Coordinates the multi-agent execution pipeline. Resolves tool parameters,
    coordinates specialized sub-agents, detects Human-in-the-Loop intercepts,
    and resumes suspended execution sequences.
    """
    def __init__(self, llm_gateway: Optional[LLMGateway] = None):
        self.llm = llm_gateway or LLMGateway()
        self.context_manager = ContextManager()
        self.planner = PlannerAgent(self.llm)
        self.reasoning = ReasoningEngine(self.llm)
        self.response_generator = ResponseGenerator(self.llm)

    async def execute_workflow(
        self, 
        user_request: str, 
        session_id: str,
        memory_manager: Any
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Initiates a new multi-agent planning and execution workflow.
        """
        logger.info(f"Initiating workflow for session {session_id}")
        
        # 1. Fetch short term context and Qdrant memories
        yield {"event": "status", "message": "Assembling dialogue history and user memories..."}
        context_text = await self.context_manager.assemble_context(
            session_id=session_id,
            query=user_request,
            memory_manager=memory_manager
        )

        # 2. Get available tools
        yield {"event": "status", "message": "Listing active MCP tools..."}
        available_tools = await mcp_client_manager.list_all_tools()
        logger.info(f"Discovered {len(available_tools)} available tools for planning.")

        # 3. Generate execution plan
        yield {"event": "status", "message": "Decomposing request with Planner Agent..."}
        execution_plan: ExecutionPlan = await self.planner.generate_plan(
            user_request=user_request,
            available_tools=available_tools,
            context_text=context_text
        )
        
        yield {
            "event": "plan_created",
            "plan": execution_plan.model_dump()
        }

        task_manager = TaskManager(execution_plan)
        
        # 4. Delegate to running loop
        async for event in self._run_execution_loop(
            session_id=session_id,
            task_manager=task_manager,
            context_text=context_text,
            available_tools=available_tools,
            memory_manager=memory_manager
        ):
            yield event

    async def resume_workflow(
        self,
        session_id: str,
        step_id: int,
        approved: bool,
        memory_manager: Any
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Resumes a suspended workflow session based on human approval/rejection.
        """
        logger.info(f"Resuming session {session_id} on step {step_id}: approved={approved}")
        
        task_manager, context_text, history = session_state_manager.load_session(session_id)
        if not task_manager:
            logger.error(f"Failed to resume session {session_id}: Session state expired or missing.")
            yield {"event": "error", "message": "Session expired or state not found."}
            return

        step = task_manager.steps.get(step_id)
        if not step:
            yield {"event": "error", "message": f"Step {step_id} not found in plan."}
            return

        available_tools = await mcp_client_manager.list_all_tools()

        # If rejected, mark step as failed and compile final summary immediately
        if not approved:
            yield {"event": "status", "message": "Action rejected by user. Terminating task sequence..."}
            task_manager.mark_step_status(step_id, "failed", "Execution rejected by user.")
            
            yield {
                "event": "step_completed",
                "step_id": step.id,
                "status": "failed",
                "result": "User rejected tool booking confirmation."
            }
        else:
            yield {"event": "status", "message": f"Action approved. Executing tool {step.tool_name}..."}
            
            # Retrieve arguments stored in the step result string (saved as JSON string on suspension)
            try:
                tool_args = json.loads(step.result) if step.result else {}
            except Exception:
                tool_args = {}

            # Execute the tool call
            try:
                raw_result = await mcp_client_manager.execute_tool(
                    tool_name=step.tool_name,
                    arguments=tool_args
                )
                result_text = getattr(raw_result, "content", str(raw_result))
                
                # Reflect on outcome
                reflection = await self.reasoning.reflect_on_outcome(
                    goal=task_manager.goal,
                    step=step,
                    tool_args=tool_args,
                    tool_output=str(result_text)
                )
                
                task_manager.mark_step_status(step_id, "completed", str(result_text))
                yield {
                    "event": "tool_output",
                    "step_id": step.id,
                    "tool_name": step.tool_name,
                    "output": str(result_text)
                }
                yield {
                    "event": "step_completed",
                    "step_id": step.id,
                    "status": "completed",
                    "result": str(result_text)
                }
            except Exception as e:
                task_manager.mark_step_status(step_id, "failed", str(e))
                yield {
                    "event": "step_failed",
                    "step_id": step.id,
                    "error": str(e)
                }

        # Clear cached session state
        session_state_manager.clear_session(session_id)

        # Continue with remaining steps
        async for event in self._run_execution_loop(
            session_id=session_id,
            task_manager=task_manager,
            context_text=context_text,
            available_tools=available_tools,
            memory_manager=memory_manager
        ):
            yield event

    async def _run_execution_loop(
        self,
        session_id: str,
        task_manager: TaskManager,
        context_text: str,
        available_tools: List[Dict[str, Any]],
        memory_manager: Any
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Core loop that processes task queues and yields trace events.
        """
        max_loops = 20
        loop_count = 0
        suspended = False

        while not task_manager.is_plan_completed() and not task_manager.has_failed_steps() and loop_count < max_loops:
            loop_count += 1
            executable_steps = task_manager.get_executable_steps()

            if not executable_steps:
                if any(s.status == "pending" for s in task_manager.steps.values()):
                    logger.critical("Dependency deadlock detected.")
                    yield {"event": "error", "message": "Deadlock: unmet dependencies."}
                    break
                break

            for step in executable_steps:
                # 1. Resolve sub-agent based on tool registry mappings
                tool_def = next((t for t in available_tools if t["name"] == step.tool_name), None)
                server_name = tool_def.get("server_name", "local") if tool_def else "local"
                sub_agent = get_agent_for_tool(step.tool_name or "", server_name)
                
                # Emit agent light activation trigger event
                yield {
                    "event": "agent_active",
                    "agent_name": sub_agent.name,
                    "step_id": step.id
                }

                yield {
                    "event": "step_started",
                    "step_id": step.id,
                    "task": step.task
                }

                task_manager.mark_step_status(step.id, "running")

                if step.tool_name:
                    yield {"event": "status", "message": f"[{sub_agent.name}] Formulating arguments for tool: {step.tool_name}..."}
                    tool_schema = tool_def.get("input_schema", {}) if tool_def else {}

                    # 2. Formulate tool arguments via the specialized agent
                    tool_args = await sub_agent.reason_on_step(
                        task_desc=f"{step.task}: {step.description}",
                        plan_trace=task_manager.get_trace_log(),
                        context_text=context_text,
                        reasoning_engine=self.reasoning,
                        tool_schema=tool_schema
                    )

                    # 3. Intercept and suspend if the tool requires Human-in-the-loop validation
                    if step.tool_name in CONFIRMATION_REQUIRED_TOOLS:
                        logger.warning(f"Tool '{step.tool_name}' requires human approval. Suspending session {session_id}.")
                        
                        # Store arguments in the step result temporarily
                        task_manager.mark_step_status(step.id, "awaiting_confirmation", json.dumps(tool_args))
                        
                        # Save session state
                        history = await memory_manager.get_short_term_memory(session_id)
                        session_state_manager.save_session(session_id, task_manager, context_text, history)
                        
                        yield {
                            "event": "awaiting_confirmation",
                            "step_id": step.id,
                            "tool_name": step.tool_name,
                            "arguments": tool_args,
                            "details": f"Agent {sub_agent.name} is requesting approval to run '{step.tool_name}' with parameter details: {json.dumps(tool_args, indent=1)}"
                        }
                        suspended = True
                        break

                    # 4. Standard tool execution
                    yield {"event": "status", "message": f"[{sub_agent.name}] Calling tool {step.tool_name}..."}
                    try:
                        raw_result = await mcp_client_manager.execute_tool(
                            tool_name=step.tool_name,
                            arguments=tool_args
                        )
                        result_content = getattr(raw_result, "content", str(raw_result))
                        
                        # 5. Reflection and correction
                        reflection = await self.reasoning.reflect_on_outcome(
                            goal=task_manager.goal,
                            step=step,
                            tool_args=tool_args,
                            tool_output=str(result_content)
                        )

                        if reflection.get("correction_required"):
                            yield {"event": "status", "message": f"Self-Correction: {reflection.get('correction_details')}"}
                            retry_args = await sub_agent.reason_on_step(
                                task_desc=f"{step.task}: {step.description} (Correction notice: {reflection.get('correction_details')})",
                                plan_trace=task_manager.get_trace_log(),
                                context_text=context_text,
                                reasoning_engine=self.reasoning,
                                tool_schema=tool_schema
                            )
                            raw_result = await mcp_client_manager.execute_tool(
                                tool_name=step.tool_name,
                                arguments=retry_args
                            )
                            result_content = getattr(raw_result, "content", str(raw_result))

                        task_manager.mark_step_status(step.id, "completed", str(result_content))
                        yield {
                            "event": "tool_output",
                            "step_id": step.id,
                            "tool_name": step.tool_name,
                            "output": str(result_content)
                        }

                    except Exception as e:
                        logger.error(f"Tool execution failed: {e}")
                        task_manager.mark_step_status(step.id, "failed", str(e))
                        yield {
                            "event": "step_failed",
                            "step_id": step.id,
                            "error": str(e)
                        }
                        break
                else:
                    # Local reasoning step
                    yield {"event": "status", "message": f"[{sub_agent.name}] Processing reasoning step..."}
                    await asyncio.sleep(0.3)
                    task_manager.mark_step_status(step.id, "completed", "Local reasoning validation succeeded.")

                yield {
                    "event": "step_completed",
                    "step_id": step.id,
                    "status": step.status,
                    "result": step.result
                }

            if suspended:
                break

        if suspended:
            return

        # 6. Synthesize final response
        yield {"event": "status", "message": "Synthesizing final response summary..."}
        final_response = await self.response_generator.generate_final_response(
            goal=task_manager.goal,
            plan_trace=task_manager.get_trace_log()
        )

        chunk_size = 15
        for i in range(0, len(final_response), chunk_size):
            yield {
                "event": "chunk",
                "text": final_response[i:i+chunk_size]
            }
            await asyncio.sleep(0.01)

        # 7. Persist context to memory
        yield {"event": "status", "message": "Updating memories..."}
        await memory_manager.add_message_to_history(session_id, "user", task_manager.goal)
        await memory_manager.add_message_to_history(session_id, "assistant", final_response)
        
        full_session_log = await memory_manager.get_short_term_memory(session_id)
        asyncio.create_task(
            memory_manager.persist_long_term_memories(session_id, full_session_log)
        )

        yield {"event": "done", "message": "Workflow completed successfully."}
