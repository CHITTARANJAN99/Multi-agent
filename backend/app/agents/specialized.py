import json
from typing import List, Dict, Any, Optional
from app.llm.gateway import LLMGateway
from app.core.logging_config import logger

class BaseSpecializedAgent:
    """
    Base class for specialized sub-agents.
    Defines system prompt identity and list of allowed MCP tools.
    """
    name: str = "Specialized Agent"
    role: str = "Assistant"
    allowed_tools: List[str] = []
    system_prompt: str = ""

    def __init__(self, llm_gateway: Optional[LLMGateway] = None):
        self.llm = llm_gateway or LLMGateway()

    async def reason_on_step(
        self, 
        task_desc: str, 
        plan_trace: str, 
        context_text: str,
        reasoning_engine: Any,
        tool_schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Formulates tool parameters using the agent's unique context prompt and allowed tools.
        """
        logger.info(f"[{self.name}] Reasoning on task: {task_desc[:50]}")
        # Build prompt messages using agent's system prompt identity
        prompt = (
            f"You are the {self.name} specializing in {self.role}.\n"
            f"{self.system_prompt}\n\n"
            f"Context: {context_text}\n"
            f"Plan Trace:\n{plan_trace}\n\n"
            f"Task: {task_desc}\n"
            f"Tool Schema: {json.dumps(tool_schema)}\n\n"
            f"Formulate the arguments to pass to this tool. Return ONLY raw JSON matching the schema."
        )
        
        try:
            # We can use the reasoning engine's json extraction on top of our specialized query
            raw_response = await self.llm.generate([
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt}
            ], temperature=0.1)
            
            cleaned = reasoning_engine._extract_json_block(raw_response)
            if not cleaned or cleaned.strip() == "{}":
                return {}
            return json.loads(cleaned)
        except Exception as e:
            logger.error(f"[{self.name}] Parameter formulation failed: {e}")
            return {}

class TravelAgent(BaseSpecializedAgent):
    name = "Travel Agent"
    role = "Travel and lodging bookings"
    allowed_tools = ["search_buses", "book_bus", "search_hotels", "book_hotel"]
    system_prompt = (
        "You are the Travel Agent. Your job is to search for bus fares, flight options, "
        "and hotel accommodations, and coordinate booking reservations. Always ensure travel date "
        "and route locations align with the user's travel plans."
    )

class ResearchAgent(BaseSpecializedAgent):
    name = "Research Agent"
    role = "Information, weather, and maps retrieval"
    allowed_tools = ["get_weather_forecast", "search_nearby_attractions", "get_route_directions"]
    system_prompt = (
        "You are the Research Agent. Your job is to fetch weather predictions, map directions, "
        "and find points of interest, restaurants, and landmarks for a destination."
    )

class ShoppingAgent(BaseSpecializedAgent):
    name = "Shopping Agent"
    role = "Product search and e-commerce purchases"
    allowed_tools = ["search_products", "purchase_product"]
    system_prompt = (
        "You are the Shopping Agent. Your job is to locate items matching the user's needs, "
        "compare ratings/prices, and initiate orders. Keep within the suggested budget constraints."
    )

class EmailAgent(BaseSpecializedAgent):
    name = "Email Agent"
    role = "Email alerts and drafts management"
    allowed_tools = ["send_email_draft", "send_email"]
    system_prompt = (
        "You are the Email Agent. Your job is to format email messages, save drafts, "
        "and dispatch email alerts with confirmation details."
    )

class CalendarAgent(BaseSpecializedAgent):
    name = "Calendar Agent"
    role = "Calendar events scheduling"
    allowed_tools = ["list_calendar_events", "create_calendar_event"]
    system_prompt = (
        "You are the Calendar Agent. Your job is to check availability schedules "
        "and register meeting/appointment slots on the user's calendar."
    )

class FinanceAgent(BaseSpecializedAgent):
    name = "Finance Agent"
    role = "Budgeting and expense calculations"
    allowed_tools = ["execute_sql_query"]  # Uses db access or local reasoning
    system_prompt = (
        "You are the Finance Agent. Your job is to compile, sum up, and audit expenses, "
        "calculate travel budgets, and output clear cost estimations."
    )

class DocumentAgent(BaseSpecializedAgent):
    name = "Document Agent"
    role = "Document processing and local file reads"
    allowed_tools = ["read_file_content", "write_file_content", "extract_pdf_text"]
    system_prompt = (
        "You are the Document Agent. Your job is to inspect local logs, write texts, "
        "and parse PDFs to extract details (receipts, reservation codes, etc.)."
    )

class BrowserAgent(BaseSpecializedAgent):
    name = "Browser Agent"
    role = "Web scraping and content analysis"
    allowed_tools = ["fetch_web_content"]
    system_prompt = (
        "You are the Browser Agent. Your job is to fetch external URL links and scrape "
        "the raw text of pages to extract facts and answer user queries."
    )

# Sub-Agent Registry
AGENT_REGISTRY: Dict[str, BaseSpecializedAgent] = {
    "travel-mcp": TravelAgent(),
    "hotel-mcp": TravelAgent(),
    "weather-mcp": ResearchAgent(),
    "maps-mcp": ResearchAgent(),
    "shopping-mcp": ShoppingAgent(),
    "email-mcp": EmailAgent(),
    "calendar-mcp": CalendarAgent(),
    "database-mcp": FinanceAgent(),
    "filesystem-mcp": DocumentAgent(),
    "pdf-mcp": DocumentAgent(),
    "browser-mcp": BrowserAgent()
}

def get_agent_for_tool(tool_name: str, server_name: str) -> BaseSpecializedAgent:
    """
    Returns the specialized sub-agent assigned to handle a specific tool/server.
    Defaults to the base specialized agent if not found in registry.
    """
    agent = AGENT_REGISTRY.get(server_name)
    if not agent:
        # Check by tool names
        for sub_agent in AGENT_REGISTRY.values():
            if tool_name in sub_agent.allowed_tools:
                return sub_agent
        return BaseSpecializedAgent()
    return agent
