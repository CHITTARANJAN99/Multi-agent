import sys
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Shopping MCP")

@mcp.tool()
async def search_products(query: str, max_price: float = 100.0) -> str:
    """
    Search for items online matching a name and maximum price threshold.
    """
    return (
        f"Shopping search results for '{query}' (limit: ${max_price}):\n"
        f"- Wildcraft Outdoor Backpack 40L: $35. Rating: 4.4/5\n"
        f"- Decathlon Rain-Resistant Windcheater: $28. Rating: 4.6/5\n"
        f"- Samsonite TSA Travel Lock (Pack of 2): $18. Rating: 4.7/5"
    )

@mcp.tool(name="purchase_product")
async def purchase_product(product_name: str, price: float, shipping_address: str) -> str:
    """
    Purchase and order the selected item. (Requires Human Confirmation!)
    """
    return (
        f"Product Purchase Completed Successfully!\n"
        f"Order Receipt:\n"
        f"- Item: {product_name}\n"
        f"- Cost: ${price}\n"
        f"- Ship to: {shipping_address}\n"
        f"- Status: PROCESSING"
    )

if __name__ == "__main__":
    mcp.run()
