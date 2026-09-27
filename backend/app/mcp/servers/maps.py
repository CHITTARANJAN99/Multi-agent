import sys
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Maps MCP")

@mcp.tool()
async def search_nearby_attractions(location: str, category: str = "tourist_places") -> str:
    """
    Search for attractions, parks, or points of interest near the location.
    Args:
        location: City or coordinate area
        category: Search type ('tourist_places', 'restaurants', 'shopping_malls')
    """
    if category == "restaurants":
        return (
            f"Top dining spots near {location}:\n"
            f"- Vidyarthi Bhavan (MTR Style Dosa): 4.7/5. Indian Classics.\n"
            f"- Truffles Gourmet Burgers: 4.5/5. Casual Dining.\n"
            f"- Mavalli Tiffin Room (MTR): 4.6/5. Heritage South Indian."
        )
    return (
        f"Popular tourist destinations and sights in {location}:\n"
        f"- Lalbagh Botanical Gardens: Historic glasshouse and lake. 1.5km.\n"
        f"- Bangalore Palace: Royal Tudor architecture. 3.2km.\n"
        f"- Visvesvaraya Museum: Interactive physics & space exhibits. 2.0km."
    )

@mcp.tool()
async def get_route_directions(origin: str, destination: str, mode: str = "driving") -> str:
    """
    Calculate travel times and path directions between origin and destination.
    Args:
        origin: Starting point address or city
        destination: Terminal point address or city
        mode: Transport type ('driving', 'walking', 'transit')
    """
    return (
        f"Route directions from {origin} to {destination} ({mode}):\n"
        f"- Estimated Time: 35 mins. Distance: 14.8 km.\n"
        f"- Turn right onto Palace Rd, head towards Cubbon Park.\n"
        f"- Merge left onto MG Road. Keep right to stay on bypass."
    )

if __name__ == "__main__":
    mcp.run()
