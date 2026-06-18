from django.conf import settings

from .base import BaseLLMClient
from .gemini import GeminiLLMClient
from .openai import OpenAILLMClient


def get_provider_name() -> str:
    return "gemini" if settings.USE_GEMINI else "openai"


def get_llm_client() -> BaseLLMClient:
    if settings.USE_GEMINI:
        return GeminiLLMClient()
    return OpenAILLMClient()

