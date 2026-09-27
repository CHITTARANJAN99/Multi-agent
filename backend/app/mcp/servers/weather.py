import sys
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Weather MCP")

@mcp.tool()
async def get_weather_forecast(city: str, days: int = 3) -> str:
    """
    Get meteorological forecast conditions for a target city.
    Args:
        city: The name of the city
        days: Number of forecast days
    """
    return (
        f"Weather forecast for {city} over the next {days} days:\n"
        f"- Day 1: Sunny. Temp: 28°C / 20°C. UV Index: High. Wind: 12km/h.\n"
        f"- Day 2: Mild cloud coverage. Temp: 26°C / 19°C. Precipitation: 10%.\n"
        f"- Day 3: Part cloudy with light evening showers. Temp: 25°C / 18°C. Precipitation: 40%."
    )

if __name__ == "__main__":
    mcp.run()
