import os
from unittest.mock import MagicMock, patch

import pytest
from litellm.exceptions import APIError

from cli_chatbot.llm.litellm_client import LiteLLMInterface


ENV = {
    "LLM_PROVIDER": "gemini",
    "LLM_MODEL": "gemini-2.5-flash",
}


class TestLiteLLMInterface:
    @patch('cli_chatbot.llm.litellm_client.load_dotenv')
    def test_builds_provider_prefixed_model(self, mock_dotenv):
        """Provider and model from the environment form LiteLLM's model id."""
        with patch.dict('os.environ', ENV, clear=True):
            llm = LiteLLMInterface()

        assert llm.provider == "gemini"
        assert llm.model == "gemini/gemini-2.5-flash"

    @patch('cli_chatbot.llm.litellm_client.load_dotenv')
    def test_model_with_prefix_is_not_prefixed_twice(self, mock_dotenv):
        """An already-prefixed model is passed through unchanged."""
        with patch.dict('os.environ', {"LLM_MODEL": "openai/gpt-4o"}, clear=True):
            llm = LiteLLMInterface()

        assert llm.provider == "openai"
        assert llm.model == "openai/gpt-4o"

    @patch('cli_chatbot.llm.litellm_client.load_dotenv')
    def test_provider_wins_when_model_id_contains_slash(self, mock_dotenv):
        """OpenRouter-style model ids contain a slash but still need the provider."""
        with patch.dict(
            'os.environ',
            {
                "LLM_PROVIDER": "openrouter",
                "LLM_MODEL": "nvidia/nemotron-3.5-lightning:free",
            },
            clear=True,
        ):
            llm = LiteLLMInterface()

        assert llm.provider == "openrouter"
        assert llm.model == "openrouter/nvidia/nemotron-3.5-lightning:free"

    @patch('cli_chatbot.llm.litellm_client.load_dotenv')
    def test_provider_prefix_is_not_duplicated(self, mock_dotenv):
        """A model already prefixed with the configured provider is unchanged."""
        with patch.dict(
            'os.environ',
            {
                "LLM_PROVIDER": "openrouter",
                "LLM_MODEL": "openrouter/nvidia/nemotron-3.5-lightning:free",
            },
            clear=True,
        ):
            llm = LiteLLMInterface()

        assert llm.model == "openrouter/nvidia/nemotron-3.5-lightning:free"

    @patch('cli_chatbot.llm.litellm_client.load_dotenv')
    def test_missing_model_raises(self, mock_dotenv):
        """A missing LLM_MODEL is reported clearly."""
        with patch.dict('os.environ', {"LLM_PROVIDER": "gemini"}, clear=True):
            with pytest.raises(ValueError, match="LLM_MODEL"):
                LiteLLMInterface()

    @patch('cli_chatbot.llm.litellm_client.load_dotenv')
    def test_missing_provider_raises(self, mock_dotenv):
        """A model without a prefix needs LLM_PROVIDER."""
        with patch.dict('os.environ', {"LLM_MODEL": "gemini-2.5-flash"}, clear=True):
            with pytest.raises(ValueError, match="LLM_PROVIDER"):
                LiteLLMInterface()

    @patch('cli_chatbot.llm.litellm_client.load_dotenv')
    def test_config_overrides_environment(self, mock_dotenv):
        """Constructor config wins over environment values."""
        with patch.dict('os.environ', ENV, clear=True):
            llm = LiteLLMInterface(
                {
                    "provider": "anthropic",
                    "model": "claude-sonnet-4",
                    "system_instruction": "Custom instruction",
                    "max_output_tokens": 2048,
                    "temperature": 0.2,
                    "api_key": "config-key",
                    "api_base": "https://example.test/v1",
                }
            )

        assert llm.model == "anthropic/claude-sonnet-4"
        assert llm.provider == "anthropic"
        assert llm.max_output_tokens == 2048
        assert llm.temperature == 0.2
        assert llm.api_key == "config-key"
        assert llm.api_base == "https://example.test/v1"

    @patch('cli_chatbot.llm.litellm_client.load_dotenv')
    @patch('cli_chatbot.llm.litellm_client.completion')
    def test_send_message_success(self, mock_completion, mock_dotenv):
        """The completion result content is returned and logged."""
        mock_completion.return_value = MagicMock()
        mock_completion.return_value.choices[0].message.content = "Test response"

        with patch.dict('os.environ', ENV, clear=True):
            llm = LiteLLMInterface()
            response = llm.send_message("Test message")

        assert response == "Test response"
        mock_completion.assert_called_once_with(
            model="gemini/gemini-2.5-flash",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Test message"},
            ],
            max_tokens=1024,
        )

    @patch('cli_chatbot.llm.litellm_client.load_dotenv')
    @patch('cli_chatbot.llm.litellm_client.completion')
    def test_send_message_uses_env_api_key(self, mock_completion, mock_dotenv):
        """LLM_API_KEY is passed through as the API key override."""
        mock_completion.return_value.choices[0].message.content = "ok"

        with patch.dict('os.environ', {**ENV, "LLM_API_KEY": "env-key"}, clear=True):
            llm = LiteLLMInterface()
            llm.send_message("Test message")

        assert mock_completion.call_args.kwargs["api_key"] == "env-key"

    @patch('cli_chatbot.llm.litellm_client.load_dotenv')
    @patch('cli_chatbot.llm.litellm_client.completion')
    def test_send_message_empty_response(self, mock_completion, mock_dotenv):
        """Empty content is reported as no response."""
        mock_completion.return_value.choices[0].message.content = None

        with patch.dict('os.environ', ENV, clear=True):
            llm = LiteLLMInterface()
            response = llm.send_message("Test message")

        assert response == "No response received"

    @patch('cli_chatbot.llm.litellm_client.load_dotenv')
    @patch('cli_chatbot.llm.litellm_client.completion')
    def test_send_message_invalid_response(self, mock_completion, mock_dotenv):
        """A malformed response is reported as an error."""
        mock_completion.return_value.choices = []

        with patch.dict('os.environ', ENV, clear=True):
            llm = LiteLLMInterface()
            response = llm.send_message("Test message")

        assert "Error" in response

    @patch('cli_chatbot.llm.litellm_client.load_dotenv')
    @patch('cli_chatbot.llm.litellm_client.completion')
    def test_send_message_api_error(self, mock_completion, mock_dotenv):
        """LiteLLM API errors are returned with an API Error prefix."""
        mock_completion.side_effect = APIError(
            status_code=429,
            message="rate limited",
            llm_provider="gemini",
            model="gemini-2.5-flash",
        )

        with patch.dict('os.environ', ENV, clear=True):
            llm = LiteLLMInterface()
            response = llm.send_message("Test message")

        assert "API Error" in response

    @patch('cli_chatbot.llm.litellm_client.load_dotenv')
    @patch('cli_chatbot.llm.litellm_client.completion')
    def test_send_message_unexpected_error(self, mock_completion, mock_dotenv):
        """Unexpected errors are returned as error strings."""
        mock_completion.side_effect = Exception("Unexpected error")

        with patch.dict('os.environ', ENV, clear=True):
            llm = LiteLLMInterface()
            response = llm.send_message("Test message")

        assert "Error" in response

    @patch('cli_chatbot.llm.litellm_client.load_dotenv')
    @patch('cli_chatbot.llm.litellm_client.completion')
    @patch('logging.Logger.info')
    def test_logging_behavior(self, mock_logger, mock_completion, mock_dotenv):
        """Requests and responses are logged."""
        mock_completion.return_value.choices[0].message.content = "Test response"

        with patch.dict('os.environ', ENV, clear=True):
            llm = LiteLLMInterface()
            llm.send_message("Test message")

        mock_logger.assert_any_call("LLM Request: Test message")
        mock_logger.assert_any_call("LLM Response: Test response")
