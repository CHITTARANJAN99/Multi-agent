import sys
import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Browser MCP")

@mcp.tool()
async def fetch_web_content(url: str) -> str:
    """
    Simulate fetching and scraping textual content of a web page URL.
    Args:
        url: Absolute URL path to retrieve
    """
    try:
        # In a real environment, we'd fetch the HTML. Here we return a clean mock text representation.
        domain = url.split("//")[-1].split("/")[0]
        return (
            f"Successfully scraped content from {domain}:\n"
            f"--- Web Content Start ---\n"
            f"Welcome to Bangalore Travel Guide! Karnataka's capital, Bangalore, is famous for "
            f"its cool year-round climate, lush botanical gardens, and microbreweries.\n"
            f"Major sights: Nandi Hills, Lalbagh botanical gardens, Vidhana Soudha Palace.\n"
            f"--- Web Content End ---"
        )
    except Exception as e:
        return f"Failed to retrieve web contents: {str(e)}"

if __name__ == "__main__":
    mcp.run()
