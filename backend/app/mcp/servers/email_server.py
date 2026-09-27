import sys
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Email MCP")

@mcp.tool()
async def send_email_draft(recipient: str, subject: str, body: str) -> str:
    """
    Prepare and save an email draft.
    """
    return (
        f"Email draft saved successfully.\n"
        f"- To: {recipient}\n"
        f"- Subject: {subject}\n"
        f"- Body preview: '{body[:60]}...'"
    )

@mcp.tool(name="send_email")
async def send_email(recipient: str, subject: str, body: str) -> str:
    """
    Send an email message immediately. (Requires Human Confirmation!)
    """
    return (
        f"Email Sent Successfully!\n"
        f"Details:\n"
        f"- To: {recipient}\n"
        f"- Subject: {subject}\n"
        f"- Status: SENT"
    )

if __name__ == "__main__":
    mcp.run()
