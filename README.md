# mcp-client

A command-line chat client that talks to Gemini and can launch MCP servers.

## What's in it

- `cli_chatbot/chat/`: the read-eval-print chat loop and a rolling history buffer capped at 2000 characters.
- `cli_chatbot/llm/`: an abstract `LLMInterface` and a Gemini implementation that defaults to `gemini-2.5-flash`.
- `cli_chatbot/mcp/`: a launcher that starts MCP servers listed in a JSON config, and helpers that exchange tool calls with a server over stdin/stdout.
- `cli_chatbot/tools/`: a tool registry plus input and output validation built on Pydantic.
- `cli_chatbot/logging_system.py`: rotating log files under `logs/`.

There is no installed package or entry point yet, so the modules are used from Python rather than a `mcp-client` command.

## Requirements

- Python 3.10 or newer.
- Packages: `google-genai`, `python-dotenv`, `pydantic` and `pytest`.
- A Gemini API key.

## Setup

Clone the repo and create a virtual environment:

```bash
git clone <repo-url> mcp-client
cd mcp-client
python -m venv .venv
source .venv/bin/activate
pip install google-genai python-dotenv pydantic pytest
```

Put your key in a `.env` file in the project root. `gemini_client.py` loads it on startup:

```
GEMINI_API_KEY=your-key-here
```

## Run a chat

Start a loop that reads from stdin until you type `exit` or `quit`:

```bash
python -c "
from cli_chatbot.chat.history import ChatHistoryManager
from cli_chatbot.chat.loop import ChatLoop
from cli_chatbot.llm.gemini_client import GeminiLLMInterface

ChatLoop(ChatHistoryManager(), GeminiLLMInterface()).run()
"
```

`GeminiLLMInterface` accepts an optional config dict with `model`, `system_instruction`, `max_output_tokens` and `tools` (a list of callables), for example `GeminiLLMInterface({"model": "gemini-2.5-pro"})`.

History is capped at 2000 characters by default: past that, the oldest messages are dropped. Raise the cap by passing `ChatHistoryManager(max_chars=...)`.

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

Tests marked `api_key` call the real Gemini API and need a valid `GEMINI_API_KEY`. Skip them with `pytest -m "not api_key"`.

## Logs

Logging is configured on first use and writes to `logs/chat.log`, `logs/llm.log`, `logs/tools.log`, `logs/mcp/filesystem.log` and `logs/mcp/other_servers.log`. Each file rotates at 1 MB and keeps 5 backups.
