"""Tests for the example MCP server and demo client."""

import asyncio
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import MagicMock

from mcp.types import CallToolResult, TextContent, Tool

REPO_ROOT = Path(__file__).parents[3]
DEMO_PATH = REPO_ROOT / "examples" / "mcp_demo.py"


def load_demo():
    spec = importlib.util.spec_from_file_location("mcp_demo", DEMO_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_demo_round_trip():
    """The demo starts the server, lists tools and calls add."""
    result = subprocess.run(
        [sys.executable, str(DEMO_PATH)],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=REPO_ROOT,
    )

    assert result.returncode == 0, result.stderr
    assert " - add:" in result.stdout
    assert " - multiply:" in result.stdout
    assert "add(a=2, b=3) -> 5.0" in result.stdout


def test_llm_demo_calls_the_tool(monkeypatch):
    """The demo's LLM mode executes the requested tool through MCP."""
    demo = load_demo()

    tool_call = MagicMock()
    tool_call.id = "call-1"
    tool_call.function.name = "multiply"
    tool_call.function.arguments = json.dumps({"a": 12, "b": 7})
    tool_call.model_dump.return_value = {
        "id": "call-1",
        "type": "function",
        "function": {"name": "multiply", "arguments": '{"a": 12, "b": 7}'},
    }

    first_message = MagicMock()
    first_message.content = None
    first_message.tool_calls = [tool_call]

    final_message = MagicMock()
    final_message.content = "The answer is 84."
    final_message.tool_calls = []

    first_response = MagicMock()
    first_response.choices[0].message = first_message
    final_response = MagicMock()
    final_response.choices[0].message = final_message

    class FakeSession:
        def __init__(self):
            self.calls = []

        async def list_tools(self):
            return MagicMock(
                tools=[
                    Tool(
                        name="multiply",
                        description="Multiply two numbers.",
                        input_schema={"type": "object"},
                    )
                ]
            )

        async def call_tool(self, name, arguments):
            self.calls.append((name, arguments))
            return CallToolResult(
                content=[TextContent(type="text", text="84.0")]
            )

    class FakeLLM:
        model = "fake/model"
        system_instruction = "You are a helpful assistant."

        def __init__(self):
            self.requests = []

        def complete(self, messages, tools=None):
            self.requests.append((list(messages), tools))
            return first_response if len(self.requests) == 1 else final_response

    fake_llm = FakeLLM()
    monkeypatch.setattr(
        "cli_chatbot.llm.litellm_client.LiteLLMInterface", lambda: fake_llm
    )

    session = FakeSession()
    asyncio.run(demo.run_llm_demo(session, "What is 12 multiplied by 7?"))

    assert session.calls == [("multiply", {"a": 12, "b": 7})]
    assert any(
        tool["function"]["name"] == "multiply"
        for tool in fake_llm.requests[0][1]
    )
    assert fake_llm.requests[1][0][-1]["role"] == "tool"
    assert fake_llm.requests[1][0][-1]["content"] == "84.0"
