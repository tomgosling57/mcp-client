"""Tests for the MCP-enabled chat loop."""

import asyncio
import json
from unittest.mock import MagicMock

from mcp.types import CallToolResult, TextContent, Tool

from cli_chatbot.chat.history import ChatHistoryManager
from cli_chatbot.chat.mcp_loop import MCPChatLoop


def make_tool_call(name="multiply", arguments=None, call_id="call-1"):
    tool_call = MagicMock()
    tool_call.id = call_id
    tool_call.function.name = name
    tool_call.function.arguments = json.dumps(arguments or {})
    tool_call.model_dump.return_value = {
        "id": call_id,
        "type": "function",
        "function": {
            "name": name,
            "arguments": json.dumps(arguments or {}),
        },
    }
    return tool_call


def make_response(content, tool_calls=None):
    message = MagicMock()
    message.content = content
    message.tool_calls = tool_calls or []
    response = MagicMock()
    response.choices[0].message = message
    return response


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
        return CallToolResult(content=[TextContent(type="text", text="84.0")])


class FakeLLM:
    model = "fake/model"
    system_instruction = "You are a helpful assistant."

    def __init__(self, responses):
        self.responses = responses
        self.requests = []

    def complete(self, messages, tools=None):
        self.requests.append((list(messages), tools))
        return self.responses.pop(0)


def test_load_tools_converts_schemas():
    """Tools from the session are converted to OpenAI-style schemas."""
    loop = MCPChatLoop(
        ChatHistoryManager(), FakeLLM([]), FakeSession()
    )

    tools = asyncio.run(loop.load_tools())

    assert loop.tool_names == ["multiply"]
    assert tools[0]["function"]["name"] == "multiply"
    assert tools[0]["function"]["parameters"] == {"type": "object"}


def test_process_message_executes_tool_calls():
    """Tool calls are run against the MCP session before the final answer."""
    llm = FakeLLM(
        [
            make_response(
                None,
                [make_tool_call("multiply", {"a": 12, "b": 7})],
            ),
            make_response("The answer is 84."),
        ]
    )
    session = FakeSession()
    history = ChatHistoryManager()
    loop = MCPChatLoop(history, llm, session)
    asyncio.run(loop.load_tools())

    result = asyncio.run(loop.process_message("What is 12 multiplied by 7?"))

    assert result == "The answer is 84."
    assert session.calls == [("multiply", {"a": 12, "b": 7})]
    assert history.messages == [
        {"role": "user", "content": "What is 12 multiplied by 7?"},
        {"role": "assistant", "content": "The answer is 84."},
    ]

    second_request = llm.requests[1][0]
    assert second_request[-2]["role"] == "assistant"
    assert second_request[-2]["tool_calls"][0]["id"] == "call-1"
    assert second_request[-1] == {
        "role": "tool",
        "tool_call_id": "call-1",
        "content": "84.0",
    }


def test_process_message_reports_llm_errors():
    """Model errors are printed and do not crash the chat."""

    class FailingLLM(FakeLLM):
        def complete(self, messages, tools=None):
            raise RuntimeError("model unavailable")

    loop = MCPChatLoop(ChatHistoryManager(), FailingLLM([]), FakeSession())

    result = asyncio.run(loop.process_message("hello"))

    assert result is None


def test_process_message_reports_tool_errors(monkeypatch):
    """Tool failures are passed back to the model as text."""

    class FailingSession(FakeSession):
        async def call_tool(self, name, arguments):
            raise RuntimeError("tool exploded")

    llm = FakeLLM(
        [
            make_response(None, [make_tool_call()]),
            make_response("Could not multiply."),
        ]
    )
    loop = MCPChatLoop(ChatHistoryManager(), llm, FailingSession())
    asyncio.run(loop.load_tools())

    asyncio.run(loop.process_message("multiply please"))

    assert llm.requests[1][0][-1]["content"] == "Tool error: tool exploded"
