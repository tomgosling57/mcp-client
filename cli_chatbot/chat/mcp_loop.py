"""Chat loop that lets the LLM call tools on a live MCP session."""

import asyncio
import json
from typing import Any, Dict, List, Optional

from cli_chatbot.chat.history import ChatHistoryManager
from cli_chatbot.llm.litellm_client import LiteLLMInterface
from cli_chatbot.mcp.tool_schema import to_openai_tool, tool_result_text

MAX_TOOL_ROUNDS = 5


class MCPChatLoop:
    """Run a CLI chat where the model can call tools from an MCP server.

    Args:
        history_manager: ChatHistoryManager instance for managing history
        llm_client: LiteLLMInterface used to talk to the model
        session: An initialized MCP ClientSession
    """

    def __init__(
        self,
        history_manager: ChatHistoryManager,
        llm_client: LiteLLMInterface,
        session: Any,
    ):
        self.history_manager = history_manager
        self.llm_client = llm_client
        self.session = session
        self.tools: List[Dict[str, Any]] = []
        self.tool_names: List[str] = []

    async def load_tools(self) -> List[Dict[str, Any]]:
        """Fetch the server's tools and convert them for LiteLLM."""
        result = await self.session.list_tools()
        self.tools = [to_openai_tool(tool) for tool in result.tools]
        self.tool_names = [tool.name for tool in result.tools]
        return self.tools

    async def run(self) -> None:
        """Run the chat loop until the user exits."""
        await self.load_tools()
        names = ", ".join(self.tool_names) if self.tool_names else "none"
        print(
            f"Chat session started with MCP tools: {names}. "
            "Type 'exit' or 'quit' to end."
        )

        while True:
            try:
                user_input = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nExiting chat...")
                break

            if user_input.lower() in ("exit", "quit"):
                print("Exiting chat...")
                break

            if not user_input:
                continue

            await self.process_message(user_input)

    async def process_message(self, user_message: str) -> Optional[str]:
        """Send one message, executing any tool calls the model requests.

        Args:
            user_message: The user's input message

        Returns:
            The assistant's final response, or None on failure
        """
        self.history_manager.add_message("user", user_message)

        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": self.llm_client.system_instruction}
        ]
        messages.extend(
            {"role": message["role"], "content": message["content"]}
            for message in self.history_manager.messages
        )

        for _ in range(MAX_TOOL_ROUNDS):
            try:
                response = await asyncio.to_thread(
                    self.llm_client.complete, messages, self.tools
                )
            except Exception as exc:
                print(f"Error: {exc}")
                return None

            message = response.choices[0].message
            assistant_message: Dict[str, Any] = {
                "role": "assistant",
                "content": message.content,
            }
            if message.tool_calls:
                assistant_message["tool_calls"] = [
                    tool_call.model_dump() for tool_call in message.tool_calls
                ]
            messages.append(assistant_message)

            if not message.tool_calls:
                content = message.content or "No response received"
                print(f"Assistant: {content}")
                self.history_manager.add_message("assistant", content)
                return content

            for tool_call in message.tool_calls:
                try:
                    arguments = json.loads(tool_call.function.arguments or "{}")
                except json.JSONDecodeError:
                    arguments = {}

                print(f"Tool call: {tool_call.function.name}({arguments})")
                try:
                    result = await self.session.call_tool(
                        tool_call.function.name, arguments
                    )
                    text = tool_result_text(result)
                except Exception as exc:
                    text = f"Tool error: {exc}"

                print(f"Tool result: {text}")
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": text,
                    }
                )

        print("Assistant: stopped after too many tool rounds")
        return None
