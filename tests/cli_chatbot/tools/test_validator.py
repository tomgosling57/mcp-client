import pytest
import json
from unittest.mock import MagicMock, patch
from pydantic import BaseModel
from cli_chatbot.tools.validator import (
    validate_tool_input,
    validate_tool_output,
    ToolRegistry,
    InvalidToolInputError,
    InvalidToolOutputError
)
from cli_chatbot.tools.schema import ToolSchema

class _TestInputModel(BaseModel):
    param1: str
    param2: int

class _TestOutputModel(BaseModel):
    result: str
    data: dict

class TestToolInputValidation:
    """Tests for tool input validation functionality."""
    
    def test_valid_tool_input(self):
        """Test validation of correctly formatted tool input."""
        valid_input = {
            "param1": "value1",
            "param2": 42
        }
        
        # Should not raise exception
        validate_tool_input(valid_input, _TestInputModel)

    def test_missing_required_field(self):
        """Test validation fails when required field is missing."""
        invalid_input = {
            "param1": "value1"
        }
        
        with pytest.raises(InvalidToolInputError):
            validate_tool_input(invalid_input, _TestInputModel)

    def test_invalid_field_type(self):
        """Test validation fails when field has wrong type."""
        invalid_input = {
            "param1": 123,  # Should be string
            "param2": 42
        }
        
        with pytest.raises(InvalidToolInputError):
            validate_tool_input(invalid_input, _TestInputModel)

class TestToolOutputValidation:
    """Tests for tool output validation functionality."""
    
    def test_valid_tool_output(self):
        """Test validation of correctly formatted tool output."""
        valid_output = {
            "result": "success",
            "data": {"key": "value"}
        }
        
        # Should not raise exception
        validate_tool_output(valid_output, _TestOutputModel)

    def test_invalid_output_structure(self):
        """Test validation fails when output has invalid structure."""
        invalid_output = {
            "result": "success",
            "data": "just a string"  # Should be dict
        }
        
        with pytest.raises(InvalidToolOutputError):
            validate_tool_output(invalid_output, _TestOutputModel)

class TestToolRegistry:
    """Tests for tool registry functionality."""
    
    @pytest.fixture
    def registry(self):
        """Fixture providing a clean ToolRegistry instance."""
        return ToolRegistry()

    def test_register_and_get_tool(self, registry):
        """Test registering and retrieving a tool."""
        tool_schema = ToolSchema(
            name="test_tool",
            input_model=_TestInputModel,
            output_model=_TestOutputModel,
            description="Test tool"
        )
        registry.register("test_tool", tool_schema)
        
        assert registry.get("test_tool") == tool_schema

    def test_get_nonexistent_tool(self, registry):
        """Test getting a tool that wasn't registered."""
        with pytest.raises(KeyError):
            registry.get("nonexistent_tool")

    def test_register_duplicate_tool(self, registry):
        """Test registering a tool with duplicate name."""
        tool_schema1 = ToolSchema(
            name="test_tool",
            input_model=_TestInputModel,
            output_model=_TestOutputModel,
            description="Test tool 1"
        )
        tool_schema2 = ToolSchema(
            name="test_tool",
            input_model=_TestInputModel,
            output_model=_TestOutputModel,
            description="Test tool 2"
        )
        
        registry.register("test_tool", tool_schema1)
        with pytest.raises(ValueError):
            registry.register("test_tool", tool_schema2)

    def test_list_tools(self, registry):
        """Test listing all registered tools."""
        tool_schema1 = ToolSchema(
            name="tool1",
            input_model=_TestInputModel,
            output_model=_TestOutputModel,
            description="Tool 1"
        )
        tool_schema2 = ToolSchema(
            name="tool2",
            input_model=_TestInputModel,
            output_model=_TestOutputModel,
            description="Tool 2"
        )
        
        registry.register("tool1", tool_schema1)
        registry.register("tool2", tool_schema2)
        
        tools = registry.list_tools()
        assert set(tools.keys()) == {"tool1", "tool2"}
        assert tools["tool1"] == tool_schema1
        assert tools["tool2"] == tool_schema2