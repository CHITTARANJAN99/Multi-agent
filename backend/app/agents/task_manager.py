from typing import List, Dict, Any, Optional
from app.agents.planner_agent import PlanStep, ExecutionPlan
from app.core.logging_config import logger

class TaskManager:
    """
    Manages state, queues, dependency resolution, and execution order of PlanSteps.
    """
    def __init__(self, plan: ExecutionPlan):
        self.goal = plan.goal
        self.steps: Dict[int, PlanStep] = {step.id: step for step in plan.steps}

    def get_executable_steps(self) -> List[PlanStep]:
        """
        Returns steps that are 'pending' and have all dependencies completed.
        """
        executable = []
        for step_id, step in self.steps.items():
            if step.status != "pending":
                continue

            # Check if all dependencies are completed
            deps_completed = True
            for dep_id in step.dependencies:
                dep_step = self.steps.get(dep_id)
                if not dep_step or dep_step.status != "completed":
                    deps_completed = False
                    break

            if deps_completed:
                executable.append(step)

        return executable

    def mark_step_status(self, step_id: int, status: str, result: Optional[str] = None) -> None:
        """
        Updates status and result for a step.
        """
        step = self.steps.get(step_id)
        if step:
            step.status = status
            if result is not None:
                step.result = result
            logger.info(f"Step {step_id} marked as {status}")

    def is_plan_completed(self) -> bool:
        """
        Returns True if all steps are successfully completed.
        """
        return all(step.status == "completed" for step in self.steps.values())

    def has_failed_steps(self) -> bool:
        """
        Returns True if any step failed.
        """
        return any(step.status == "failed" for step in self.steps.values())

    def get_trace_log(self) -> str:
        """
        Compiles the current history of step execution results for model review.
        """
        trace_lines = []
        for step_id in sorted(self.steps.keys()):
            step = self.steps[step_id]
            status_symbol = "✓" if step.status == "completed" else "✗" if step.status == "failed" else "•"
            result_summary = step.result[:150] + "..." if step.result and len(step.result) > 150 else step.result or "No result."
            trace_lines.append(
                f"Step {step.id} [{status_symbol} {step.status}]: {step.task}\n"
                f"  Description: {step.description}\n"
                f"  Tool Called: {step.tool_name or 'Local Reasoner'}\n"
                f"  Result: {result_summary}\n"
            )
        return "\n".join(trace_lines)
