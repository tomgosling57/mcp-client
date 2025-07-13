import os
from unittest.mock import patch, MagicMock
import pytest
from google.genai.errors import APIError
from google.genai import types
from cli_chatbot.llm.gemini_client import GeminiLLMInterface

class TestGeminiLLMInterface:
    @pytest.mark.api_key
    @patch('dotenv.load_dotenv')
    @patch('google.genai.Client')
    def test_loads_api_key_from_environment(self, mock_client, mock_dotenv):
        """Test that GeminiClient loads API key from environment variables."""
        with patch.dict('os.environ', {'GEMINI_API_KEY': 'test-env-key'}, clear=True):
            GeminiLLMInterface()
            mock_client.assert_called_once_with('gemini-2.5-flash', api_key='test-env-key')

    @pytest.mark.api_key
    @patch('cli_chatbot.llm.gemini_client.load_dotenv')
    @patch('google.genai.Client')
    def test_loads_api_key_from_dotenv(self, mock_client, mock_dotenv):
        """Test that GeminiClient loads API key from .env file when environment is empty."""
        def mock_load_dotenv():
            os.environ['GEMINI_API_KEY'] = 'test-dotenv-key'
            return True
        mock_dotenv.side_effect = mock_load_dotenv

        with patch.dict('os.environ', {'GEMINI_API_KEY': 'test-dotenv-key'}, clear=True):
        
        
            # Verify environment was populated
            assert os.environ['GEMINI_API_KEY'] == 'test-dotenv-key'
            
            # Initialize client and verify proper API key usage
            GeminiLLMInterface()
            
            # Verify both dotenv loading and client initialization
            mock_dotenv.assert_called_once()
            mock_client.assert_called_once_with('gemini-2.5-flash', api_key='test-dotenv-key')

    @patch('google.genai.Client')
    def test_send_message_success(self, mock_client):
        """Test successful message sending and response handling."""
        mock_response = MagicMock()
        mock_response.text = "Test response"
        mock_client.return_value.generate_content.return_value = mock_response

        llm = GeminiLLMInterface()
        response = llm.send_message("Test message")
        
        assert response == "Test response"
        mock_client.return_value.generate_content.assert_called_once_with(
            contents=["Test message"],
            config=types.GenerateContentConfig(
                tools=[],
                maxOutputTokens=1024,
                system_instruction="You are a helpful assistant."
            )
        )

    @patch('google.genai.Client')
    def test_send_message_empty_response(self, mock_client):
        """Test handling of empty response from API."""
        mock_client.return_value.generate_content.return_value = None

        llm = GeminiLLMInterface()
        response = llm.send_message("Test message")
        
        assert response == "No response received"

    @patch('google.genai.Client')
    def test_send_message_invalid_response(self, mock_client):
        """Test handling of invalid response structure."""
        mock_response = MagicMock()
        del mock_response.text
        mock_client.return_value.generate_content.return_value = mock_response

        llm = GeminiLLMInterface()
        response = llm.send_message("Test message")
        
        assert response == "Invalid response structure"

    @patch('google.genai.Client')
    def test_send_message_api_error(self, mock_client):
        """Test handling of API errors."""
        mock_client.return_value.generate_content.side_effect = APIError("API error", dict())

        llm = GeminiLLMInterface()
        response = llm.send_message("Test message")
        
        assert "API Error" in response

    @patch('google.genai.Client')
    def test_send_message_unexpected_error(self, mock_client):
        """Test handling of unexpected errors."""
        mock_client.return_value.generate_content.side_effect = Exception("Unexpected error")

        llm = GeminiLLMInterface()
        response = llm.send_message("Test message")
        
        assert "Error" in response

    @patch('google.genai.Client')
    def test_custom_configuration(self, mock_client):
        """Test initialization with custom configuration."""
        test_tool = types.Tool(
            function_declarations=[types.FunctionDeclaration(
                name='test_tool',
                description='Test tool description',
                parameters={'type': 'OBJECT', 'properties': {}}
            )]
        )
        
        config = {
            'model': 'gemini-2.0-pro',
            'system_instruction': 'Custom instruction',
            'max_output_tokens': 2048,
            'tools': [test_tool]
        }

        llm = GeminiLLMInterface(config=config)
        
        # Verify client initialized with correct model
        mock_client.assert_called_once_with('gemini-2.0-pro', api_key=os.getenv('GEMINI_API_KEY'))
        
        # Verify generation config
        response = llm.send_message("Test message")
        mock_client.return_value.generate_content.assert_called_once_with(
            contents=["Test message"],
            config=types.GenerateContentConfig(
                tools=[test_tool],
                maxOutputTokens=2048,
                system_instruction='Custom instruction'
            )
        )

    @patch('google.genai.Client')
    @patch('logging.Logger.info')
    def test_logging_behavior(self, mock_logger, mock_client):
        """Test that messages and responses are properly logged."""
        mock_response = MagicMock()
        mock_response.text = "Test response"
        mock_client.return_value.generate_content.return_value = mock_response

        llm = GeminiLLMInterface()
        response = llm.send_message("Test message")
        
        # Verify request and response logging
        mock_logger.assert_any_call("LLM Request: Test message")
        mock_logger.assert_any_call("LLM Response: Test response")