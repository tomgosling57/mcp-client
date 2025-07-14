import json
import subprocess
import logging
import threading
from typing import Dict, List, Optional, Union
from pathlib import Path

class ServerLauncher:
    """Handles loading and launching MCP servers from configuration.
    
    Attributes:
        workspace_path: Path to workspace directory for resolving ${workspaceFolder}
        logger: Configured logger instance for process output
    """
    
    def __init__(self, workspace_path: str = "c:/Software/mcp/clients/gemini"):
        """Initialize the server launcher.
        
        Args:
            workspace_path: Path to workspace directory (default: current workspace)
        """
        self.workspace_path = workspace_path
        self._setup_logging()
        
    def _setup_logging(self, test_mode: bool = False) -> None:
        """Configure logging for server processes.
        
        Args:
            test_mode: If True, disables console output and sets higher log level
        """
        self.logger = logging.getLogger('mcp.server_launcher')
        if not self.logger.handlers:
            if test_mode:
                self.logger.setLevel(logging.WARNING)
                # Add NullHandler to suppress output
                self.logger.addHandler(logging.NullHandler())
            else:
                self.logger.setLevel(logging.INFO)
                handler = logging.StreamHandler()
                handler.setFormatter(logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                ))
                self.logger.addHandler(handler)
    
    def read_servers_json(self, filename: str) -> Dict:
        """Read and parse servers.json configuration file.
        
        Args:
            filename: Path to JSON configuration file
            
        Returns:
            Parsed JSON content as dictionary
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            json.JSONDecodeError: If config file contains invalid JSON
        """
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError as e:
            self.logger.error(f"Config file not found: {filename}")
            raise
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in config file: {filename}")
            raise
    
    def _resolve_workspace_path(self, parts: List[str]) -> List[str]:
        """Replace ${workspaceFolder} placeholders in command parts.
        
        Args:
            parts: List of command/argument parts
            
        Returns:
            List with placeholders resolved to actual workspace path
        """
        return [part.replace("${workspaceFolder}", self.workspace_path) 
                for part in parts]
    
    class StreamLogger:
        """Helper class to manage logging from a stream in a background thread."""
        
        def __init__(self, stream, logger_method, test_mode=False):
            self.stream = stream
            self.logger_method = logger_method
            self._thread = None
            self._test_mode = test_mode
            self._stop_event = threading.Event()
            
        def _log_stream(self):
            """Thread target function to read and log stream output."""
            try:
                while not self._stop_event.is_set():
                    try:
                        line = self.stream.readline()
                        if not line:  # Empty string means EOF
                            break
                        if not self._test_mode:  # Skip actual logging in test mode
                            self.logger_method(line.strip())
                    except ValueError as e:
                        if "I/O operation on closed file" in str(e):
                            break
                        raise
                    except (AttributeError, RuntimeError):
                        # Handle cases where stream is closed during read
                        break
            finally:
                self._close_stream()
                
        def _close_stream(self):
            """Safely close the stream."""
            try:
                self.stream.close()
            except:
                pass
                
        def start(self):
            """Start the logging thread."""
            self._thread = threading.Thread(
                target=self._log_stream,
                daemon=True
            )
            self._thread.start()
            
        def stop(self):
            """Stop the logging thread."""
            self._stop_event.set()
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=0.1)
            self._close_stream()
            
        def stop(self):
            """Stop the logging thread and cleanup resources."""
            if self._thread and self._thread.is_alive():
                self._close_stream()
                self._thread.join(timeout=0.1)
                
        def __enter__(self):
            """Context manager entry."""
            self.start()
            return self
            
        def __exit__(self, exc_type, exc_val, exc_tb):
            """Context manager exit."""
            self.stop()
            
    def _start_output_logger(self,
                          stream: subprocess.PIPE,
                          logger_method: callable) -> StreamLogger:
        """Start thread to log process output.
        
        Args:
            stream: Process stdout or stderr stream
            logger_method: Logger method to use (info/error)
            
        Returns:
            StreamLogger instance managing the logging thread
        """
        return self.StreamLogger(stream, logger_method)
    
    def launch_server(self, server_config: Dict) -> subprocess.Popen:
        """Launch an MCP server as a subprocess.
        
        Args:
            server_config: Dictionary containing server configuration
                Required keys:
                - name: Server name
                - type: Server type ('stdio' or 'sse')
                - command: List of command parts
                - args: List of command arguments
                
        Returns:
            The created subprocess.Popen object
            
        Raises:
            KeyError: If required config keys are missing
            subprocess.SubprocessError: If process fails to start
        """
        try:
            command = self._resolve_workspace_path(server_config['command'])
            args = self._resolve_workspace_path(server_config['args'])
            full_command = command + args
            
            process = subprocess.Popen(
                full_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1
            )
            
            with self._start_output_logger(process.stdout, self.logger.info), \
                 self._start_output_logger(process.stderr, self.logger.error):
                pass  # Context managers handle thread lifecycle
            
            return process
            
        except KeyError as e:
            self.logger.error(f"Missing required config key: {e}")
            raise
        except subprocess.SubprocessError as e:
            self.logger.error(f"Failed to launch server: {e}")
            raise