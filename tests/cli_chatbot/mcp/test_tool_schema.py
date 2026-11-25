"""Tests for MCP tool schema helpers."""

from mcp.types import CallToolResult, TextContent, Tool

from cli_chatbot.mcp.tool_schema import to_openai_tool, tool_result_text


def test_to_openai_tool():
    """MCP tools are converted to OpenAI-style tool schemas."""
    tool = Tool(
        name="add",
        description="Add two numbers.",
        input_schema={
            "type": "object",
            "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
            "required": ["a", "b"],
        },
    )

    schema = to_openai_tool(tool)

    assert schema == {
        "type": "function",
        "function": {
            "name": "add",
            "description": "Add two numbers.",
            "parameters": tool.input_schema,
        },
    }


def test_tool_result_text():
    """Text content from an MCP tool result is flattened."""
    result = CallToolResult(content=[TextContent(type="text", text="5.0")])

    assert tool_result_text(result) == "5.0"


def test_tool_result_text_without_text():
    """Results without text content still produce a readable string."""
    result = CallToolResult(content=[])

    assert tool_result_text(result) == "(no text content)"
