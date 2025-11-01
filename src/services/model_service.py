from langchain_openai import ChatOpenAI
from src.core.config import get_settings


class ModelService:
    def __init__(self):
        self.settings = get_settings()
        self._model = None

    def get_model(self, model_name: str = None, temperature: float = None):
        model_name = model_name or self.settings.model_name
        temperature = temperature or self.settings.model_temperature

        if self.settings.custom_model_enabled:
            return ChatOpenAI(
                model=self.settings.custom_model_name,
                temperature=temperature,
                api_key=self.settings.custom_model_api_key,
                base_url=self.settings.custom_model_base_url,
            )

        if "gpt" in model_name:
            return ChatOpenAI(
                model=model_name, temperature=temperature, api_key=self.settings.openai_api_key
            )
        else:
            raise ValueError(f"Unknown model: {model_name}")


model_service = ModelService()
