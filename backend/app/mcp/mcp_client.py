import json
import os
import sys
import asyncio
from contextlib import AsyncExitStack
from typing import Dict, Any, List, Optional
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from app.config.settings import settings
from app.core.logging_config import logger
from app.core.errors import MCPClientError

class MCPClientManager:
    """
    Manages connections and tool invocations across multiple Model Context Protocol (MCP) servers.
    Handles startup parameters, session lifetime management, and tool call routing.
    """
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or settings.MCP_CONFIG_PATH
        self.sessions: Dict[str, ClientSession] = {}
        self.tool_to_server_map: Dict[str, str] = {}
        self._exit_stack = AsyncExitStack()

    async def start(self) -> None:
        """
        Loads the configuration file and establishes connections with all configured MCP servers.
        """
        if not os.path.exists(self.config_path):
            logger.warning(f"MCP configuration file not found at {self.config_path}. No MCP servers initialized.")
            return

        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
        except Exception as e:
            logger.error(f"Failed to read MCP config: {e}")
            raise MCPClientError("Malformed MCP config file", detail=str(e))

        mcp_servers = config.get("mcpServers", {})
        logger.info(f"Discovered {len(mcp_servers)} MCP server configurations. Starting connection loops...")

        for server_name, server_config in mcp_servers.items():
            await self._connect_to_server(server_name, server_config)

    async def _connect_to_server(self, server_name: str, server_config: Dict[str, Any]) -> None:
        """
        Connects to a single MCP server (stdio transport client wrapper) and indexes its tools.
        """
        command = server_config.get("command")
        args = server_config.get("args", [])
        env = {**os.environ, **server_config.get("env", {})}

        if not command:
            logger.error(f"Skipping MCP server '{server_name}': command execution key missing.")
            return

        if command in ("python", "python3"):
            command = sys.executable

        # Resolve server script paths relative to backend directory if relative
        resolved_args = []
        for arg in args:
            if arg.endswith(".py") and not os.path.isabs(arg):
                # Check if it exists relative to cwd or backend
                if not os.path.exists(arg):
                    alt_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), arg)
                    if os.path.exists(alt_path):
                        resolved_args.append(alt_path)
                        continue
            resolved_args.append(arg)
        args = resolved_args

        logger.info(f"Connecting to MCP server '{server_name}' using: {command} {' '.join(args)}")

        try:
            server_params = StdioServerParameters(
                command=command,
                args=args,
                env=env
            )
            # Enter stdio transport context
            transport = await self._exit_stack.enter_async_context(stdio_client(server_params))
            read_stream, write_stream = transport
            
            # Enter Session context
            session = await self._exit_stack.enter_async_context(ClientSession(read_stream, write_stream))
            await session.initialize()
            
            self.sessions[server_name] = session
            logger.info(f"Connected to MCP server: {server_name}")
            
            # Discover and map available tools
            await self._discover_server_tools(server_name)
        except Exception as e:
            logger.error(f"Could not connect to MCP server '{server_name}': {e}", exc_info=True)
            # Do not raise, allow other servers to connect

    async def _discover_server_tools(self, server_name: str) -> None:
        """
        Queries an MCP server for its list of tools and indexes them.
        """
        session = self.sessions.get(server_name)
        if not session:
            return

        try:
            tools_response = await session.list_tools()
            tools_list = tools_response.tools if hasattr(tools_response, "tools") else getattr(tools_response, "tools", [])
            
            logger.info(f"Discovered {len(tools_list)} tools from MCP server '{server_name}'")
            
            for tool in tools_list:
                tool_name = tool.name
                self.tool_to_server_map[tool_name] = server_name
                logger.debug(f"Mapped tool '{tool_name}' to server '{server_name}'")
        except Exception as e:
            logger.error(f"Failed to list tools from server '{server_name}': {e}")

    async def list_all_tools(self) -> List[Dict[str, Any]]:
        """
        Aggregates and returns the list of all tools across all connected MCP servers.
        """
        all_tools = []
        for server_name, session in self.sessions.items():
            try:
                tools_response = await session.list_tools()
                tools_list = tools_response.tools if hasattr(tools_response, "tools") else getattr(tools_response, "tools", [])
                for t in tools_list:
                    all_tools.append({
                        "server_name": server_name,
                        "name": t.name,
                        "description": t.description,
                        "input_schema": t.inputSchema
                    })
            except Exception as e:
                logger.error(f"Error listing tools for {server_name}: {e}")
        return all_tools

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Invokes an MCP tool by auto-routing to the server holding the definition.
        """
        server_name = self.tool_to_server_map.get(tool_name)
        if not server_name:
            raise MCPClientError(f"Tool '{tool_name}' not found on any active MCP server.")

        session = self.sessions.get(server_name)
        if not session:
            raise MCPClientError(f"Session for MCP server '{server_name}' is inactive.")

        logger.info(f"Routing execution: calling tool '{tool_name}' on server '{server_name}'")
        try:
            result = await session.call_tool(tool_name, arguments)
            return result
        except Exception as e:
            logger.error(f"Failed to execute tool '{tool_name}' on server '{server_name}': {e}")
            raise MCPClientError(f"Execution error on tool '{tool_name}': {str(e)}")

    async def stop(self) -> None:
        """
        Cleans up connection stack references and shuts down processes.
        """
        logger.info("Stopping MCP client manager and disconnecting server sessions...")
        await self._exit_stack.aclose()
        self.sessions.clear()
        self.tool_to_server_map.clear()
        logger.info("All MCP sessions terminated.")

mcp_client_manager = MCPClientManager()
