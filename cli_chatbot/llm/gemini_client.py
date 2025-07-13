import logging
from typing import Optional, Dict, Any, List, Callable
from .interface import LLMInterface
from google import genai
from google.genai.errors import APIError
import os
from dotenv import load_dotenv


class GeminiLLMInterface(LLMInterface):
    """Concrete implementation of LLMInterface for Gemini API."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the Gemini client with configuration.

        Args:
            config: Optional configuration dictionary with keys:
                - model: Model name (default: 'gemini-2.5-flash')
                - system_instruction: System prompt for the model
                - generation_config: Generation parameters like temperature
        """
        super().__init__()
        if not config: 
            config = {}
                
        # Load environment variables from .env file
        load_dotenv()
        
        # Set default model configuration
        self.model = 'gemini-2.5-flash'
        if 'model' in config:
            self.model = config['model']
            
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not found. Please set it in your environment or .env file")
        self.client = genai.Client(self.model, api_key=api_key)
        self.model = config.get('model', 'gemini-2.5-flash') if config else 'gemini-2.5-flash'
        self.system_instruction = config.get('system_instruction', "You are a helpful assistant.")
        # Handle generation config
        self.generation_config = genai.types.GenerateContentConfig(
            tools=config.get('tools', []),
            maxOutputTokens=config.get('max_output_tokens', 1024),
            system_instruction=self.system_instruction,
        )
    def send_message(self, message: str, tools: Optional[List[Callable]] = None) -> str:
        """Send a message to the Gemini LLM and return its response.
        
        Args:
            message: The input message to send to the LLM
            tools: Optional list of Python callable functions the model may use
            
        Returns:
            The LLM's text response or error message string
        """
        logger = logging.getLogger()
        logger.info(f"LLM Request: {message}")
        
        try:
            response = self.client.generate_content(
                contents=[message],
                config=self.generation_config
            )
            
            if not response:
                logger.error("Empty response from Gemini model")
                return "No response received"
                
            if hasattr(response, 'text') and response.text:
                logger.info(f"LLM Response: {response.text}")
                return response.text
                
            logger.error("Invalid response structure from Gemini model")
            return "Invalid response structure"
            
        except APIError as e:
            logger.error(f"Gemini API error: {e}")
            return f"API Error: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error in GeminiLLMInterface: {e}")
            return f"Error: {str(e)}"