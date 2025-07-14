import pytest
import json
import logging
import time
from unittest.mock import MagicMock, patch, call
from cli_chatbot.mcp.server_launcher import ServerLauncher

@pytest.fixture
def mock_servers_config(tmp_path):
    """Fixture providing a temporary servers.json file."""
    config = {
        "servers": [{
            "name": "filesystem",
            "type": "stdio",
            "command": ["python", "-m", "mcp.servers.filesystem"],
            "args": ["${workspaceFolder}/workspace/"]
        }]
    }
    config_file = tmp_path / "servers.json"
    config_file.write_text(json.dumps(config))
    return str(config_file)

def test_read_servers_json_success(mock_servers_config):
    """Test successful reading of servers.json."""
    launcher = ServerLauncher()
    content = launcher.read_servers_json(mock_servers_config)
    assert "servers" in content
    assert len(content["servers"]) == 1
    assert content["servers"][0]["name"] == "filesystem"

def test_read_servers_json_file_not_found():
    """Test handling of missing config file."""
    launcher = ServerLauncher()
    with pytest.raises(FileNotFoundError):
        launcher.read_servers_json("nonexistent.json")

def test_read_servers_json_invalid_json(tmp_path):
    """Test handling of invalid JSON."""
    invalid_file = tmp_path / "invalid.json"
    invalid_file.write_text("{invalid}")
    launcher = ServerLauncher()
    with pytest.raises(json.JSONDecodeError):
        launcher.read_servers_json(str(invalid_file))

@patch('subprocess.Popen')
def test_launch_server_success(mock_popen):
    """Test successful server launch."""
    launcher = ServerLauncher()
    mock_config = {
        "name": "mock-server",
        "type": "stdio",
        "command": ["python", "-m", "mock.server"],
        "args": []
    }
    
    process = launcher.launch_server(mock_config)
    mock_popen.assert_called_once()
    assert process == mock_popen.return_value

@patch('subprocess.Popen')
def test_workspace_path_resolution(mock_popen):
    """Test ${workspaceFolder} placeholder resolution."""
    launcher = ServerLauncher(workspace_path="/test/path")
    mock_config = {
        "name": "filesystem",
        "type": "stdio",
        "command": ["python", "-m", "mcp.servers.filesystem"],
        "args": ["${workspaceFolder}/workspace/"]
    }
    
    launcher.launch_server(mock_config)
    called_args = mock_popen.call_args[0][0]
    assert "/test/path/workspace/" in called_args[-1]

@patch('subprocess.Popen')
@patch('cli_chatbot.mcp.server_launcher.logging.getLogger')
def test_output_capture(mock_logger, mock_popen):
    """Test stdout/stderr capture and logging."""
    # Setup mock process with proper file-like output streams
    mock_process = MagicMock()
    
    # Create mock stdout/stderr with readline() behavior
    stdout_lines = ["stdout line 1\n", "stdout line 2\n"]
    stderr_lines = ["stderr line 1\n"]
    
    mock_process.stdout = MagicMock()
    mock_process.stdout.readline = MagicMock(side_effect=stdout_lines + [""])
    mock_process.stdout.close = MagicMock()
    
    mock_process.stderr = MagicMock()
    mock_process.stderr.readline = MagicMock(side_effect=stderr_lines + [""])
    mock_process.stderr.close = MagicMock()
    
    mock_popen.return_value = mock_process
    
    # Setup real logger to test stream handling
    logger = logging.getLogger('test')
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(message)s'))
    logger.addHandler(handler)
    mock_logger.return_value = logger
    
    launcher = ServerLauncher()
    mock_config = {
        "name": "test-server",
        "type": "stdio",
        "command": ["python", "-c", "print('test')"],
        "args": []
    }
    
    # Close handler to simulate the error condition
    handler.close()
    
    # Should not raise ValueError
    launcher.launch_server(mock_config)
    
    # Verify streams were closed
    mock_process.stdout.close.assert_called_once()
    mock_process.stderr.close.assert_called_once()

def test_stream_logger_basic():
    """Test StreamLogger basic functionality."""
    mock_stream = MagicMock()
    mock_stream.readline = MagicMock(side_effect=["line 1\n", "line 2\n", ""])
    mock_stream.close = MagicMock()
    
    mock_logger = MagicMock()
    
    with ServerLauncher.StreamLogger(mock_stream, mock_logger) as logger:
        # Give thread time to process
        time.sleep(0.1)
        
    # Verify lines were logged
    mock_logger.assert_has_calls([
        call("line 1"),
        call("line 2")
    ])
    
    # Verify stream was closed
    assert mock_stream.close.call_count >= 1

def test_stream_logger_error_handling():
    """Test StreamLogger handles closed file errors."""
    mock_stream = MagicMock()
    mock_stream.readline = MagicMock(side_effect=ValueError("I/O operation on closed file"))
    mock_stream.close = MagicMock()
    
    mock_logger = MagicMock()
    
    logger = ServerLauncher.StreamLogger(mock_stream, mock_logger)
    logger.start()
    logger.stop()
    
    # Should not raise and should close stream
    mock_stream.close.assert_called_once()

def test_launch_server_missing_config():
    """Test handling of missing required config keys."""
    launcher = ServerLauncher()
    with pytest.raises(KeyError):
        launcher.launch_server({"name": "incomplete"})