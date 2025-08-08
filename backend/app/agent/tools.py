from typing import Callable, Dict, Any
from .models import ToolSchema


class MCPTool:
    """Represents a tool in the (MCP)."""
    def __init__(self, name: str, description: str, method: Callable, input_schema: Dict[str, Any] = None):
        self.name = name
        self.description = description
        self.method = method
        self.input_schema = input_schema or {}

    async def execute(self, **kwargs) -> Any:
        """Execute the tool with the provided arguments."""
        # Validate input against schema if provided
        if self.input_schema:
            try:
                ToolSchema(parameters=kwargs)
            except ValueError as e:
                raise ValueError(f"Invalid input for tool {self.name}: {str(e)}")
        return await self.method(**kwargs)