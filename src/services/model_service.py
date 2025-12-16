"""
Model Service - LLM Client Management

Handles initialization of language model clients based on configuration.
Supports both Ollama (local) and custom/OpenAI-compatible endpoints.

Configuration Priority:
1. If CUSTOM_MODEL_ENABLED=true → Use custom endpoint
2. Otherwise → Use Ollama with MODEL_NAME setting
"""

import logging
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from src.core.config import get_settings

logger = logging.getLogger(__name__)


class ModelService:
    """Manages LLM client initialization based on configuration."""

    def __init__(self):
        """Initialize ModelService with current settings."""
        self.settings = get_settings()
        self._model = None
        self._log_configuration()

    def _log_configuration(self) -> None:
        """Log current model configuration for debugging."""
        if self.settings.custom_model_enabled:
            logger.info(
                f"✓ Using custom model endpoint"
                f"\n  Base URL: {self.settings.custom_model_base_url}"
                f"\n  Model: {self.settings.custom_model_name}"
            )
        else:
            logger.info(
                f"✓ Using Ollama"
                f"\n  Model: {self.settings.model_name}"
                f"\n  Temperature: {self.settings.model_temperature}"
            )

    def get_model(self, model_name: str = None, temperature: float = None):
        """
        Get or create an LLM client based on configuration.

        Configuration is resolved in this priority:
        1. Function parameters (model_name, temperature)
        2. Custom model settings (if enabled)
        3. Default Ollama settings

        Args:
            model_name: Override model name (optional)
            temperature: Override temperature (optional)

        Returns:
            ChatOpenAI or ChatOllama instance configured and ready to use
        """
        # Use provided parameters or fall back to settings
        temperature = temperature or self.settings.model_temperature

        # Determine which LLM to use
        if self.settings.custom_model_enabled:
            # Use custom endpoint (e.g., custom OpenAI-compatible API)
            logger.debug(
                f"Creating ChatOpenAI client for custom endpoint: {self.settings.custom_model_base_url}"
            )

            model_to_use = model_name or self.settings.custom_model_name

            return ChatOpenAI(
                model=model_to_use,
                temperature=temperature,
                api_key=self.settings.custom_model_api_key,
                base_url=self.settings.custom_model_base_url,
                reasoning=False,
            )
        else:
            # Use Ollama (local model)
            logger.debug(f"Creating ChatOllama client")

            model_to_use = model_name or self.settings.model_name
            logger.debug(f"  Model: {model_to_use}")
            logger.debug(f"  Temperature: {temperature}")

            return ChatOllama(
                model=model_to_use,
                temperature=temperature,
                reasoning=False,
            )


# Create singleton instance
model_service = ModelService()
