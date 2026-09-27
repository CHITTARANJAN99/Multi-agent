import sys
from mcp.server.fastmcp import FastMCP

# Instantiate FastMCP server
mcp = FastMCP("Travel MCP")

@mcp.tool()
async def search_buses(source: str, destination: str, date: str) -> str:
    """
    Search for available buses between the source and destination on a given date.
    Args:
        source: Starting city name
        destination: Target city name
        date: Date of travel (YYYY-MM-DD format)
    """
    return (
        f"Available buses from {source} to {destination} on {date}:\n"
        f"- KSRTC Swift AC Sleeper: Departs 21:00, Arrives 06:00, Price: $18, Rating: 4.5/5\n"
        f"- SRS Travels Semi-Sleeper: Departs 22:30, Arrives 07:30, Price: $12, Rating: 4.1/5\n"
        f"- National Travels Multi-Axle: Departs 23:00, Arrives 08:00, Price: $15, Rating: 4.3/5"
    )

@mcp.tool(name="book_bus")
async def book_bus(bus_line: str, source: str, destination: str, date: str, passenger_name: str) -> str:
    """
    Confirm and book a ticket for the selected bus line. (Requires Human Confirmation!)
    """
    return (
        f"Booking Confirmation Successful!\n"
        f"Ticket Details:\n"
        f"- Passenger: {passenger_name}\n"
        f"- Bus Line: {bus_line}\n"
        f"- Route: {source} -> {destination}\n"
        f"- Date: {date}\n"
        f"- Status: CONFIRMED"
    )

if __name__ == "__main__":
    mcp.run()
