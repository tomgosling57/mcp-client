"""Start the example calculator MCP server and talk to it.

Without arguments this runs the plain MCP round trip: initialize, list tools,
and call ``add(2, 3)``.

    python examples/mcp_demo.py

With ``--ask`` it also lets the configured LiteLLM model pick a tool, calls it
through MCP, and prints the final answer:

    python examples/mcp_demo.py --ask "What is 12 multiplied by 7?"
"""

import argparse
import asyncio
from pathlib import Path
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import Tool

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from cli_chatbot.mcp.tool_schema import tool_result_text

SERVER_PATH = Path(__file__).with_name("calculator_server.py")


async def list_tools(session: ClientSession) -> list[Tool]:
    result = await session.list_tools()
    return result.tools


async def run_tools_demo(session: ClientSession) -> None:
    """List the server's tools and call one directly."""
    tools = await list_tools(session)

    print("Connected to the calculator MCP server.")
    print("Tools:")
    for tool in tools:
        print(f"  - {tool.name}: {tool.description}")

    result = await session.call_tool("add", {"a": 2, "b": 3})
    print(f"\nadd(a=2, b=3) -> {tool_result_text(result)}")


async def run_llm_demo(session: ClientSession, prompt: str) -> None:
    """Let the configured model call MCP tools until it has an answer."""
    from cli_chatbot.chat.history import ChatHistoryManager
    from cli_chatbot.chat.mcp_loop import MCPChatLoop
    from cli_chatbot.llm.litellm_client import LiteLLMInterface

    llm = LiteLLMInterface()
    loop = MCPChatLoop(ChatHistoryManager(), llm, session)
    await loop.load_tools()

    print(f"Model: {llm.model}")
    await loop.process_message(prompt)


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Demonstrate the example calculator MCP server."
    )
    parser.add_argument(
        "--ask",
        metavar="PROMPT",
        help="Ask the configured LiteLLM model, letting it call MCP tools.",
    )
    args = parser.parse_args()

    server = StdioServerParameters(
        command=sys.executable,
        args=[str(SERVER_PATH)],
    )

    async with stdio_client(server) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            if args.ask:
                await run_llm_demo(session, args.ask)
            else:
                await run_tools_demo(session)


if __name__ == "__main__":
    asyncio.run(main())
