import sys
import json

def process_tool_call(tool_call: dict) -> None:
    """Process a tool call by writing it to stdout as JSON."""
    json.dump(tool_call, sys.stdout)
    sys.stdout.write('\n')
    sys.stdout.flush()

def read_tool_result() -> dict:
    """Read a tool result from stdin as JSON and return it."""
    line = sys.stdin.readline()
    return json.loads(line)