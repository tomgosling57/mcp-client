import logging
from abc import ABC, abstractmethod
from cli_chatbot.logging_system import configure_logging

class LLMInterface(ABC):
    """Abstract base class for LLM interfaces in the CLI chatbot."""
    
    def __init__(self):
        configure_logging()
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def send_message(self, message: str) -> str:
        """Send a message to the LLM and return its response.
        
        Args:
            message: The input message to send to the LLM
            
        Returns:
            The LLM's response as a string
        """
        raise NotImplementedError