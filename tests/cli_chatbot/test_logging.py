import os
import unittest 
from unittest.mock import call
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import json

class TestLogging(unittest.TestCase):
    def setUp(self):
        """Clean up and recreate test directories before each test."""
        test_log_dir = Path("logs")
        if test_log_dir.exists():
            for root, dirs, files in os.walk(test_log_dir, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
            os.rmdir(test_log_dir)
        # Ensure logs directory exists
        test_log_dir.mkdir(exist_ok=True)

    def test_log_directory_creation(self):
        """Test that log directories are created correctly."""
        # Test paths
        log_dir = Path("logs")
        mcp_log_dir = log_dir / "mcp"

        # Create directories
        log_dir.mkdir(exist_ok=True)
        mcp_log_dir.mkdir(exist_ok=True)

        # Verify directories exist
        self.assertTrue(log_dir.exists(), "logs/ directory was not created")
        self.assertTrue(mcp_log_dir.exists(), "logs/mcp/ directory was not created")

    def test_basic_file_logging(self):
        """Test basic file logging functionality."""
        from cli_chatbot.logging_system import configure_logging
        
        # Configure logger using actual implementation with custom rotation params
        configure_logging(max_bytes=100, backup_count=1, test_mode=True)
        logging.getLogger().setLevel(logging.INFO)
        
        try:
            # Write test message
            test_message = "Test log message from test_basic_file_logging"
            logging.info(test_message)

            # Verify file exists and contains message
            log_file = Path("logs/chat.log")
            self.assertTrue(log_file.exists(), "Log file was not created")
            with open(log_file, 'r') as f:
                log_content = f.read()
            self.assertIn(test_message, log_content, "Log message not found in file")
            self.assertIn("root", log_content, "Logger name not in log output")
            
            # Verify rotation params are respected
            for i in range(10):  # Write enough to trigger rotation
                logging.info(f"Rotation test message {i}")
            
            backup_file = Path("logs/chat.log.1")
            self.assertTrue(backup_file.exists(), "Backup file was not created")
            self.assertFalse(Path("logs/chat.log.2").exists(),
                           "Too many backup files created")
        finally:
            # Properly shutdown logging to release file handles
            logging.shutdown()

    def test_additional_log_files(self):
        """Test that all additional log files are created."""
        from cli_chatbot.logging_system import configure_logging
        
        # Configure logger
        configure_logging(llm_logging=True, test_mode=True)
        
        try:
            # Verify standard log files exist
            for log_name in ["chat.log", "llm.log", "tools.log"]:
                log_file = Path("logs") / log_name
                self.assertTrue(log_file.exists(),
                               f"{log_name} was not created")
            
            # Verify MCP log files exist in mcp subdirectory
            for log_name in ["filesystem.log", "other_servers.log"]:
                log_file = Path("logs") / "mcp" / log_name
                self.assertTrue(log_file.exists(),
                               f"mcp/{log_name} was not created")
        finally:
            logging.shutdown()

    def test_llm_logging(self):
        """Test that LLM interactions are properly logged."""
        from unittest.mock import patch
        from cli_chatbot.logging_system import configure_logging
        from cli_chatbot.llm.gemini_client import GeminiLLMInterface

        # Configure logging for LLM
        configure_logging(llm_logging=True, test_mode=True)

        try:
            test_request = "Test LLM request"
            
            # Mock the logger and Gemini client
            with patch('logging.getLogger') as mock_get_logger, \
                 patch('cli_chatbot.llm.gemini_client.genai.Client') as mock_client:
                mock_logger = mock_get_logger.return_value
                
                # Setup mock response
                mock_response = type('MockResponse', (), {'text': 'Mock response'})
                mock_client.return_value.generate_content.return_value = mock_response
                
                # Create and test LLM instance
                llm = GeminiLLMInterface()
                llm.send_message(test_request)
                
                # Verify logger was called with expected messages in order
                expected_calls = [
                    call(f"LLM Request: {test_request}"),
                    call("LLM Response: Mock response")
                ]
                mock_logger.info.assert_has_calls(expected_calls)
        finally:
            # Properly shutdown logging to release file handles
            logging.shutdown()

    def tearDown(self):
        """Clean up test directories after each test."""
        from cli_chatbot.logging_system import shutdown_logging
        shutdown_logging()
        
        test_log_dir = Path("logs")
        if test_log_dir.exists():
            # Retry cleanup with delay to handle Windows file locking
            for attempt in range(3):
                try:
                    for root, dirs, files in os.walk(test_log_dir, topdown=False):
                        for name in files:
                            os.remove(os.path.join(root, name))
                        for name in dirs:
                            os.rmdir(os.path.join(root, name))
                    os.rmdir(test_log_dir)
                    break
                except PermissionError:
                    if attempt == 2:  # Last attempt
                        raise
                    import time
                    time.sleep(0.1)

    def test_log_rotation(self):
        """Test that log rotation works correctly."""
        # Configure rotating file handler
        log_file = Path("logs/rotation.log")
        handler = RotatingFileHandler(
            log_file,
            maxBytes=100,  # Small size to trigger rotation quickly
            backupCount=2
        )
        handler.setFormatter(logging.Formatter('%(message)s'))
        logger = logging.getLogger('rotation_test')
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)

        try:
            # Write enough messages to trigger rotation
            for i in range(1, 11):
                logger.info(f"Test message {i}")

            # Verify files exist
            self.assertTrue(log_file.exists(), "Main log file missing")
            backup1 = Path("logs/rotation.log.1")
            backup2 = Path("logs/rotation.log.2")
            self.assertTrue(backup1.exists(), "First backup file missing")
            self.assertFalse(backup2.exists(), "Too many backup files created")

            # Verify content distribution
            with open(log_file) as f:
                latest_content = f.read()
            with open(backup1) as f:
                backup_content = f.read()

            self.assertIn("Test message 10", latest_content, "Latest message not in main file")
            self.assertIn("Test message 1", backup_content, "Oldest message not in backup")
        finally:
            # Clean up handlers
            logger.removeHandler(handler)
            handler.close()

    def test_json_logging(self):
        """Test JSON formatted logging with extra attributes."""
        # Configure JSON logging
        log_file = Path("logs/json.log")
        handler = logging.FileHandler(log_file)
        handler.setFormatter(logging.Formatter(
            '{"time": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"}'
        ))
        logger = logging.getLogger('json_test')
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)

        try:
            # Log simple test message
            test_msg = "Test JSON log message"
            logger.info(test_msg)

            # Verify file exists
            self.assertTrue(log_file.exists(), "JSON log file was not created")

            # Read and verify basic JSON structure
            with open(log_file, 'r') as f:
                log_content = f.read()
                self.assertTrue(log_content.startswith('{"time":'))
                self.assertIn('"level": "INFO"', log_content)
                self.assertIn(f'"message": "{test_msg}"', log_content)
        finally:
            # Clean up handlers
            logger.removeHandler(handler)
            handler.close()

if __name__ == "__main__":
    unittest.main()