import json
import uuid
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

from app.core.auth import get_current_user, UserSession
from app.workflows.orchestrator import orchestrator
from app.core.logging_config import logger

router = APIRouter(prefix="/agent", tags=["Agent Execution"])

class ChatRequest(BaseModel):
    message: str = Field(..., description="The user's query or prompt to direct the agent")
    session_id: Optional[str] = Field(None, description="Active conversation session ID")

@router.post("/chat")
async def chat_endpoint(
    request: ChatRequest,
    current_user: UserSession = Depends(get_current_user)
):
    """
    Executes the multi-agent planning & tool-calling workflow.
    Streams progress logs, planning structures, tool executions, and the final LLM response.
    """
    session_id = request.session_id or f"sess_{uuid.uuid4()}"
    logger.info(f"Agent chat request received: session_id={session_id} by user={current_user.user_id}")

    async def event_generator():
        try:
            # We yield data in server-sent events format (SSE)
            async for event in orchestrator.execute(request.message, session_id):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            logger.error(f"Error in chat stream event generator: {e}", exc_info=True)
            yield f"data: {json.dumps({'event': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

class ConfirmRequest(BaseModel):
    session_id: str
    step_id: int
    approved: bool

@router.post("/confirm")
async def confirm_endpoint(
    request: ConfirmRequest,
    current_user: UserSession = Depends(get_current_user)
):
    """
    Resumes a suspended agent execution workflow with user confirmation.
    Streams remaining progress logs, tool executions, and the final synthesis response.
    """
    logger.info(f"Confirm request received for session {request.session_id}: step {request.step_id}, approved={request.approved}")

    async def event_generator():
        try:
            async for event in orchestrator.resume(
                session_id=request.session_id,
                step_id=request.step_id,
                approved=request.approved
            ):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            logger.error(f"Error in chat resume stream: {e}", exc_info=True)
            yield f"data: {json.dumps({'event': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
