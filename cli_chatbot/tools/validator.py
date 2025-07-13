from typing import Dict, Any, Optional, Type
from pydantic import ValidationError, BaseModel
from .schema import ToolSchema

class InvalidToolInputError(Exception):
    """Raised when tool input fails validation."""
    pass

class InvalidToolOutputError(Exception):
    """Raised when tool output fails validation."""
    pass

class ToolRegistry:
    """Registry for managing tool schemas and validation."""
    
    def __init__(self):
        self._tools: Dict[str, ToolSchema] = {}

    def register(self, tool_name: str, tool_schema: ToolSchema) -> None:
        """Register a tool with its validation schema.
        
        Args:
            tool_name: Name of the tool
            tool_schema: Schema for input/output validation
            
        Raises:
            ValueError: If tool with same name already registered
        """
        if tool_name in self._tools:
            raise ValueError(f"Tool '{tool_name}' already registered")
        self._tools[tool_name] = tool_schema

    def get(self, tool_name: str) -> ToolSchema:
        """Get the schema for a registered tool.
        
        Args:
            tool_name: Name of the tool to retrieve
            
        Returns:
            The tool's schema
            
        Raises:
            KeyError: If tool not found
        """
        if tool_name not in self._tools:
            raise KeyError(f"Tool '{tool_name}' not found")
        return self._tools[tool_name]

    def list_tools(self) -> Dict[str, ToolSchema]:
        """List all registered tools and their schemas.
        
        Returns:
            Dictionary mapping tool names to their schemas
        """
        return self._tools.copy()

def validate_tool_input(input_data: Dict[str, Any], schema: Type[BaseModel]) -> None:
    """Validate tool input against schema.
    
    Args:
        input_data: Input data to validate (as dict)
        schema: Pydantic model class for input validation
        
    Raises:
        InvalidToolInputError: If validation fails
    """
    try:
        schema(**input_data)
    except ValidationError as e:
        raise InvalidToolInputError(f"Invalid tool input: {e.errors()}") from e

def validate_tool_output(output_data: Dict[str, Any], schema: Type[BaseModel]) -> None:
    """Validate tool output against schema.
    
    Args:
        output_data: Output data to validate (as dict)
        schema: Pydantic model class for output validation
        
    Raises:
        InvalidToolOutputError: If validation fails
    """
    try:
        schema(**output_data)
    except ValidationError as e:
        raise InvalidToolOutputError(f"Invalid tool output: {e.errors()}") from e