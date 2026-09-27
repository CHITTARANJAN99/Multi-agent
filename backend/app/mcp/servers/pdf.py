import sys
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("PDF MCP")

@mcp.tool()
async def extract_pdf_text(pdf_path: str) -> str:
    """
    Parse a PDF document and extract readable texts.
    Args:
        pdf_path: File path of the target PDF
    """
    return (
        f"Extracted Text from PDF: {pdf_path}\n"
        f"--- Page 1 ---\n"
        f"CONFIRMATION RECEIPT:\n"
        f"Reservation Code: BLR-HOTEL-7798\n"
        f"Hotel Name: Emerald Boutique Inn, Bangalore\n"
        f"Check-In: 2026-07-17\n"
        f"Check-Out: 2026-07-19\n"
        f"Total Paid: $150.00"
    )

if __name__ == "__main__":
    mcp.run()
