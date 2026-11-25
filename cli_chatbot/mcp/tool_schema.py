"""Conversion helpers between MCP and OpenAI-style tool definitions."""

from mcp.types import CallToolResult, Tool


def to_openai_tool(tool: Tool) -> dict:
    """Convert an MCP tool definition to an OpenAI-compatible tool schema."""
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description or "",
            "parameters": tool.input_schema,
        },
    }


def tool_result_text(result: CallToolResult) -> str:
    """Flatten a tool result's text content into a single string."""
    parts = [
        content.text
        for content in result.content
        if getattr(content, "text", None)
    ]
    return "\n".join(parts) if parts else "(no text content)"
