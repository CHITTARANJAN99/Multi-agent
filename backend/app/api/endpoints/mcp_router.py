from fastapi import APIRouter, Depends
from typing import List, Dict, Any

from app.core.auth import get_current_user, UserSession
from app.mcp.mcp_client import mcp_client_manager

router = APIRouter(prefix="/mcp", tags=["Model Context Protocol"])

@router.get("/tools")
async def list_tools_endpoint(
    current_user: UserSession = Depends(get_current_user)
):
    """
    Returns lists of all tools discovered across connected MCP Servers.
    """
    tools = await mcp_client_manager.list_all_tools()
    return {
        "success": True,
        "total_tools": len(tools),
        "tools": tools
    }

@router.get("/servers")
async def list_servers_endpoint(
    current_user: UserSession = Depends(get_current_user)
):
    """
    Returns active connected MCP server names.
    """
    return {
        "success": True,
        "servers": list(mcp_client_manager.sessions.keys())
    }
