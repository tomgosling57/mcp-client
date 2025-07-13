from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, Type

class ToolSchema(BaseModel):
    """Complete schema for a tool including input and output validation."""
    name: str = Field(..., description="Name of the tool")
    input_model: Type[BaseModel] = Field(..., description="Input validation model class")
    output_model: Type[BaseModel] = Field(..., description="Output validation model class")
    description: Optional[str] = Field(None, description="Description of the tool's purpose")