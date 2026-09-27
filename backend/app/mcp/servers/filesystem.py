import sys
import os
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Filesystem MCP")

@mcp.tool()
async def read_file_content(path: str) -> str:
    """
    Read contents of a file on the local filesystem.
    Args:
        path: File path string
    """
    # Safe checks for sandbox directories
    if ".." in path or path.startswith("/") or ":" in path:
        return "Access Denied: Path must be relative and inside workspace."
    
    if not os.path.exists(path):
        return f"Error: File not found at path: {path}"
        
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"

@mcp.tool()
async def write_file_content(path: str, content: str) -> str:
    """
    Write or append text content to a local file.
    Args:
        path: File path string
        content: Text content to write
    """
    if ".." in path or path.startswith("/") or ":" in path:
        return "Access Denied: Path must be relative and inside workspace."
        
    try:
        # Create directories if they do not exist
        dir_name = os.path.dirname(path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
            
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully wrote {len(content)} characters to {path}"
    except Exception as e:
        return f"Error writing file: {str(e)}"

if __name__ == "__main__":
    mcp.run()
