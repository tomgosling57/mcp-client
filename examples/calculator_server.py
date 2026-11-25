"""A minimal MCP server exposing calculator tools over stdio.

Run it directly:

    python examples/calculator_server.py

MCP clients start it the same way and speak JSON-RPC over stdin/stdout, so the
server must not print anything else to stdout.
"""

from mcp.server import MCPServer

mcp = MCPServer(
    "calculator",
    instructions="A tiny calculator. Use the tools for arithmetic.",
)


@mcp.tool()
def add(a: float, b: float) -> float:
    """Add two numbers and return the sum."""
    return a + b


@mcp.tool()
def multiply(a: float, b: float) -> float:
    """Multiply two numbers and return the product."""
    return a * b


if __name__ == "__main__":
    mcp.run()
