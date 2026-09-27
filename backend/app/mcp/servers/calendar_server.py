import sys
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Calendar MCP")

@mcp.tool()
async def list_calendar_events(start_date: str, end_date: str) -> str:
    """
    List events scheduled in the user's calendar within a date window.
    """
    return (
        f"Scheduled events ({start_date} to {end_date}):\n"
        f"- 2026-07-17 10:00 - 11:30: Multi-Agent Arch review session\n"
        f"- 2026-07-17 14:00 - 15:00: Demo rehearsal presentation"
    )

@mcp.tool(name="create_calendar_event")
async def create_calendar_event(title: str, start_time: str, end_time: str, description: str = "") -> str:
    """
    Schedule a new meeting event in the calendar. (Requires Human Confirmation!)
    """
    return (
        f"Calendar Event Successfully Created!\n"
        f"Details:\n"
        f"- Title: {title}\n"
        f"- Time: {start_time} to {end_time}\n"
        f"- Info: {description}\n"
        f"- Status: SCHEDULED"
    )

if __name__ == "__main__":
    mcp.run()
