import sys
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Hotel MCP")

@mcp.tool()
async def search_hotels(location: str, check_in: str, check_out: str, rating: float = 4.0) -> str:
    """
    Find available hotel accommodations near a target location or coordinates.
    Args:
        location: City or area to search in
        check_in: Check-in date (YYYY-MM-DD)
        check_out: Check-out date (YYYY-MM-DD)
        rating: Minimum hotel rating out of 5
    """
    return (
        f"Accommodations found in {location} ({check_in} to {check_out}):\n"
        f"- Radisson Luxury Suites (4.6/5): $90/night. 1.2km from center. Free Wi-Fi & Breakfast.\n"
        f"- The Grand Residency (4.2/5): $55/night. 2.5km from center. Spa & Fitness room.\n"
        f"- Emerald Boutique Inn (4.4/5): $75/night. Near arrival point. Rooftop dining."
    )

@mcp.tool(name="book_hotel")
async def book_hotel(hotel_name: str, location: str, check_in: str, check_out: str, guest_name: str) -> str:
    """
    Reserve and book a room at the selected hotel. (Requires Human Confirmation!)
    """
    return (
        f"Hotel Reservation Successful!\n"
        f"Details:\n"
        f"- Hotel: {hotel_name} ({location})\n"
        f"- Guest: {guest_name}\n"
        f"- Dates: {check_in} to {check_out}\n"
        f"- Status: BOOKED"
    )

if __name__ == "__main__":
    mcp.run()
