# mcp-client

A command-line chat client that talks to any [LiteLLM](https://docs.litellm.ai/)-supported model and can launch MCP servers. The model and provider are set with environment variables. The `start` script runs the chat with the example calculator MCP server attached by default.

## What's in it

- `start`: launches the MCP-enabled chat with the example calculator server.
- `cli_chatbot/chat/`: the plain chat loop, the MCP tool-calling loop, and a rolling history buffer capped at 2000 characters.
- `cli_chatbot/llm/`: an abstract `LLMInterface` and a `LiteLLMInterface` that reads `LLM_PROVIDER` and `LLM_MODEL` from the environment.
- `cli_chatbot/mcp/`: a launcher that starts MCP servers listed in a JSON config, tool schema helpers, and helpers that exchange tool calls with a server over stdin/stdout.
- `cli_chatbot/tools/`: a tool registry plus input and output validation built on Pydantic.
- `cli_chatbot/logging_system.py`: rotating log files under `logs/`.
- `examples/`: a small MCP calculator server and a demo client that exercises it.

There is no installed package; use the `start` script or import the modules from Python.

## Requirements

- Python 3.10 or newer.
- Packages: `litellm`, `mcp`, `python-dotenv`, `pydantic` and `pytest`.
- An API key for whichever provider you configure.

## Setup

Clone the repo and create a virtual environment:

```bash
git clone <repo-url> mcp-client
cd mcp-client
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in your provider, model and key. `litellm_client.py` loads it on startup:

```
LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.5-flash
LLM_API_KEY=your-key-here
```

`LLM_PROVIDER` and `LLM_MODEL` are combined into LiteLLM's `provider/model` id (`gemini/gemini-2.5-flash` above). You can also put the full prefixed id in `LLM_MODEL` and omit `LLM_PROVIDER`:

```
LLM_MODEL=openai/gpt-4o
```

When `LLM_PROVIDER` is set it always wins, which matters for model ids that contain a slash themselves, such as OpenRouter models:

```
LLM_PROVIDER=openrouter
LLM_MODEL=nvidia/nemotron-3.5-lightning:free
LLM_API_KEY=sk-or-...
```

`LLM_API_KEY` is optional. When it is unset, LiteLLM uses the provider's usual key, such as `GEMINI_API_KEY` or `OPENAI_API_KEY`. Other optional variables are `LLM_MAX_TOKENS` (default 1024), `LLM_TEMPERATURE`, `LLM_API_BASE` for providers with a custom endpoint, and `LOG_LEVEL` (default `WARNING`).

## Run a chat

The `start` script launches the calculator MCP server and a chat session that can call its `add` and `multiply` tools by default:

```bash
./start
```

```
Chat session started with MCP tools: add, multiply. Type 'exit' or 'quit' to end.
You: What is 12 multiplied by 7?
Tool call: multiply({'a': 12, 'b': 7})
Tool result: 84.0
Assistant: 12 multiplied by 7 is 84.
You: exit
Exiting chat...
```

`start` runs from the project root, uses `.venv/bin/python` when it exists, and falls back to `python3` otherwise. The configured model must support tool calling. If it does not, the tool call fails with the provider's error and the chat stays up.

The MCP loop lives in `cli_chatbot/chat/mcp_loop.py`. It loads the server's tools, sends their schemas to LiteLLM, executes any requested tool calls over MCP, and feeds the results back until the model answers. Only the user and assistant messages go into history; tool traffic stays within the turn.

For a plain chat without MCP tools:

```bash
python -c "
from cli_chatbot.chat.history import ChatHistoryManager
from cli_chatbot.chat.loop import ChatLoop
from cli_chatbot.llm.litellm_client import LiteLLMInterface

ChatLoop(ChatHistoryManager(), LiteLLMInterface()).run()
"
```

`LiteLLMInterface` accepts an optional config dict with `provider`, `model`, `system_instruction`, `max_output_tokens`, `temperature`, `api_key` and `api_base`. Values in the dict take precedence over the environment, for example `LiteLLMInterface({"provider": "anthropic", "model": "claude-sonnet-4"})`.

History is capped at 2000 characters by default: past that, the oldest messages are dropped. Raise the cap by passing `ChatHistoryManager(max_chars=...)`.

## Example MCP server

`examples/calculator_server.py` is a minimal stdio MCP server built on the official `mcp` SDK. It exposes two tools, `add` and `multiply`, and is the server `start` launches by default.

`examples/mcp_demo.py` starts that server, connects over stdio, lists the tools and calls one:

```bash
python examples/mcp_demo.py
```

```
Connected to the calculator MCP server.
Tools:
  - add: Add two numbers and return the sum.
  - multiply: Multiply two numbers and return the product.

add(a=2, b=3) -> 5.0
```

Pass `--ask` to let your configured model select a tool, call it through MCP, and answer with the result:

```bash
python examples/mcp_demo.py --ask "What is 12 multiplied by 7?"
```

This uses the same `LLM_PROVIDER` / `LLM_MODEL` setup as the chat, and the model must support tool calling. Any MCP client can also run the server directly with `python examples/calculator_server.py` over stdio.

The demo uses the official MCP client instead of `ServerLauncher` because `ServerLauncher` consumes the subprocess's stdout for logging, so protocol messages never reach the caller.

## Launch MCP servers

`ServerLauncher` starts each server as a subprocess and writes its output to the log files. It reads a JSON config with `name`, `type`, `command` and `args` per server, and replaces `${workspaceFolder}` in the command with the workspace path:

```bash
python -c "
from cli_chatbot.mcp.server_launcher import ServerLauncher

launcher = ServerLauncher(workspace_path='/path/to/workspace')
config = launcher.read_servers_json('servers.json')
process = launcher.launch_server(config['servers'][0])
"
```

A single entry in `servers.json` looks like this:

```json
{
  "servers": [
    {
      "name": "filesystem",
      "type": "stdio",
      "command": ["npx"],
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "${workspaceFolder}"]
    }
  ]
}
```

Pass `workspace_path` explicitly. The constructor default points at a path on someone else's machine.

## Run the tests

```bash
pytest
```

The LLM tests mock `litellm.completion`, so they do not call a real API or need a key.

## Logs

Logging is configured on first use and writes to `logs/chat.log`, `logs/llm.log`, `logs/tools.log`, `logs/mcp/filesystem.log` and `logs/mcp/other_servers.log`. Each file rotates at 1 MB and keeps 5 backups.

The default level is `WARNING`, so info-level chatter (LLM requests and responses, server output) stays out of both the console and the log files. Set `LOG_LEVEL` to see more or less:

```bash
LOG_LEVEL=INFO      # LLM request/response lines and server output
LOG_LEVEL=DEBUG     # everything
LOG_LEVEL=ERROR     # errors only
```
