import sys
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Database MCP")

@mcp.tool()
async def execute_sql_query(query: str) -> str:
    """
    Run read-only SQL queries on the localized database structure.
    Args:
        query: SQL string query statement (e.g. SELECT * FROM users)
    """
    # Safe guard checks
    query_lower = query.lower()
    if any(kw in query_lower for kw in ["drop", "delete", "truncate", "update", "insert"]):
        return "Access Denied: Only read-only SELECT queries are allowed."
        
    return (
        f"Query Executed: '{query}'\n"
        f"Results:\n"
        f"| user_id | email | created_at |\n"
        f"| usr_1 | developer@agentic.ai | 2026-07-12T07:51:34Z |\n"
        f"| usr_2 | admin@agentic.ai | 2026-07-12T07:55:00Z |"
    )

if __name__ == "__main__":
    mcp.run()
