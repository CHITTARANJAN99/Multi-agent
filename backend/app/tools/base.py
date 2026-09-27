import abc
from typing import Any, Dict, Type
from pydantic import BaseModel

class BaseTool(abc.ABC):
    """
    Abstract Base Class for defining local/native tools that run directly in the backend
    (distinct from tools dynamically loaded through external MCP servers).
    """
    
    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Name of the tool."""
        pass

    @property
    @abc.abstractmethod
    def description(self) -> str:
        """Brief description detailing tool purpose and execution effects."""
        pass

    @property
    @abc.abstractmethod
    def args_schema(self) -> Type[BaseModel]:
        """Pydantic model schema defining tool input arguments."""
        pass

    @abc.abstractmethod
    async def execute(self, **kwargs) -> Any:
        """
        Executes the tool's core logic asynchronously.
        """
        pass

    def to_mcp_format(self) -> Dict[str, Any]:
        """
        Formats the native tool definition to match standard MCP schema formats.
        """
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.args_schema.model_json_schema()
        }
