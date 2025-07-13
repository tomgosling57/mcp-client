import os
import logging
import json
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime

class JsonFormatter(logging.Formatter):
    """Custom formatter that outputs logs in JSON format."""
    
    def format(self, record):
        """Format log record as JSON."""
        log_data = {
            'timestamp': datetime.utcfromtimestamp(record.created).isoformat(),
            'name': record.name,
            'level': record.levelname,
            'message': record.getMessage(),
            'pathname': record.pathname,
            'lineno': record.lineno,
            'funcName': record.funcName
        }
        
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
            
        return json.dumps(log_data)

def setup_logging_dirs():
    """Create logging directories if they don't exist."""
    log_dir = Path("logs")
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        return str(log_dir.absolute())
    except OSError as e:
        logging.error(f"Failed to create logging directories: {e}")
        raise

def configure_logging(llm_logging=False, max_bytes=1048576, backup_count=5, json_format=False):
    """Configure logging setup with rotation.
    
    Args:
        llm_logging: If True, configures additional logging for LLM interactions
        max_bytes: Maximum log file size before rotation (default: 1MB)
        backup_count: Number of backup logs to keep (default: 5)
        json_format: If True, outputs logs in JSON format (default: False)
    """
    log_dir = setup_logging_dirs()
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Remove any existing handlers to prevent duplicates
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)
    
    # Common formatter for all handlers
    formatter = JsonFormatter() if json_format else logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Main chat logging with rotation
    chat_handler = RotatingFileHandler(
        Path(log_dir) / "chat.log",
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    chat_handler.setFormatter(formatter)
    logger.addHandler(chat_handler)
    
    # Optional LLM logging with rotation
    if llm_logging:
        llm_handler = RotatingFileHandler(
            Path(log_dir) / "llm.log",
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        llm_handler.setFormatter(formatter)
        logger.addHandler(llm_handler)
    
    # Tools logging with rotation
    tools_handler = RotatingFileHandler(
        Path(log_dir) / "tools.log",
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    tools_handler.setFormatter(formatter)
    logger.addHandler(tools_handler)
    
    # Filesystem logging with rotation
    fs_handler = RotatingFileHandler(
        Path(log_dir) / "filesystem.log",
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    fs_handler.setFormatter(formatter)
    logger.addHandler(fs_handler)
    
    # Other servers logging with rotation
    servers_handler = RotatingFileHandler(
        Path(log_dir) / "other_servers.log",
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    servers_handler.setFormatter(formatter)
    logger.addHandler(servers_handler)

def shutdown_logging():
    """Properly shutdown logging by closing all handlers."""
    logger = logging.getLogger()
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)