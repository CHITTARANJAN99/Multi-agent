import sys
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("GitHub MCP")

@mcp.tool()
async def list_repo_issues(owner: str, repo: str) -> str:
    """
    Fetch open issues in a target GitHub repository.
    """
    return (
        f"Open issues in {owner}/{repo}:\n"
        f"- #45: Bug: LLM Gateway fails to parse Claude streaming outputs. Labels: critical.\n"
        f"- #48: Feature Request: Support parallel MCP tool calling. Labels: enhancement."
    )

@mcp.tool()
async def create_repo_issue(owner: str, repo: str, title: str, body: str) -> str:
    """
    Create a new issue inside the repository.
    """
    return (
        f"Issue successfully created in {owner}/{repo}:\n"
        f"- Title: {title}\n"
        f"- Issue Number: #49\n"
        f"- State: OPEN"
    )

if __name__ == "__main__":
    mcp.run()
