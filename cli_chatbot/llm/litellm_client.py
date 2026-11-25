import logging
import os
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from litellm import completion
from litellm.exceptions import APIError

from cli_chatbot.logging_system import configure_logging
from .interface import LLMInterface


class LiteLLMInterface(LLMInterface):
    """LLMInterface backed by LiteLLM.

    The provider and model come from the LLM_PROVIDER and LLM_MODEL environment
    variables, or from the config dict passed to the constructor (which wins).

    Args:
        config: Optional configuration dictionary with keys:
            - provider: Provider prefix, e.g. "gemini", "openai", "anthropic"
            - model: Model name, with or without the provider prefix
            - system_instruction: System prompt for the model
            - max_output_tokens: Maximum response tokens (default: 1024)
            - temperature: Sampling temperature (default: provider default)
            - api_key: API key override (default: LLM_API_KEY, then LiteLLM's
              provider-specific key such as GEMINI_API_KEY or OPENAI_API_KEY)
            - api_base: Custom API base URL (default: LLM_API_BASE)
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        configure_logging(llm_logging=True)
        super().__init__()
        config = config or {}

        load_dotenv()

        provider = (
            config.get("provider") or os.getenv("LLM_PROVIDER") or ""
        ).strip().rstrip("/")
        model = (config.get("model") or os.getenv("LLM_MODEL") or "").strip()
        if not model:
            raise ValueError(
                "LLM_MODEL environment variable not found. Set it in your "
                "environment or .env file, e.g. LLM_MODEL=gemini-2.5-flash"
            )

        # LiteLLM expects "provider/model". An explicitly configured provider
        # always wins, because some model ids contain a slash themselves, such
        # as OpenRouter's "nvidia/nemotron-...:free".
        if provider:
            if not model.startswith(f"{provider}/"):
                model = f"{provider}/{model}"
        elif "/" not in model:
            raise ValueError(
                "LLM_PROVIDER environment variable not found. Set it in your "
                "environment or .env file, e.g. LLM_PROVIDER=gemini"
            )

        self.provider = model.split("/", 1)[0]
        self.model = model
        self.system_instruction = config.get(
            "system_instruction", "You are a helpful assistant."
        )
        self.max_output_tokens = int(
            config.get("max_output_tokens")
            or os.getenv("LLM_MAX_TOKENS")
            or 1024
        )
        temperature = config.get("temperature")
        if temperature is None:
            temperature = os.getenv("LLM_TEMPERATURE") or None
        self.temperature = float(temperature) if temperature is not None else None
        self.api_key = config.get("api_key") or os.getenv("LLM_API_KEY")
        self.api_base = config.get("api_base") or os.getenv("LLM_API_BASE")

    def complete(
        self,
        messages: list,
        tools: Optional[list] = None,
    ):
        """Call LiteLLM with pre-built messages and optional tool schemas.

        Unlike send_message, this returns the raw LiteLLM response so callers
        can inspect tool calls. Errors are raised, not converted to strings.

        Args:
            messages: OpenAI-format messages
            tools: Optional OpenAI-format tool schemas

        Returns:
            The raw LiteLLM completion response
        """
        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_output_tokens,
        }
        if tools:
            kwargs["tools"] = tools
        if self.temperature is not None:
            kwargs["temperature"] = self.temperature
        if self.api_key:
            kwargs["api_key"] = self.api_key
        if self.api_base:
            kwargs["api_base"] = self.api_base

        return completion(**kwargs)

    def send_message(self, message: str) -> str:
        """Send a message to the configured model and return its response.

        Args:
            message: The input message to send to the LLM

        Returns:
            The LLM's text response or error message string
        """
        logger = logging.getLogger(__name__)
        logger.info(f"LLM Request: {message}")

        messages = [
            {"role": "system", "content": self.system_instruction},
            {"role": "user", "content": message},
        ]

        try:
            response = self.complete(messages)
            content = response.choices[0].message.content

            if not content:
                logger.error("Empty response from LLM")
                return "No response received"

            logger.info(f"LLM Response: {content}")
            return content

        except APIError as e:
            logger.error(f"LLM API error: {e}")
            return f"API Error: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error in LiteLLMInterface: {e}")
            return f"Error: {str(e)}"
