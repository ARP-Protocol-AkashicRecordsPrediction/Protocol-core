import hashlib
from typing import Optional

from django.conf import settings

from simulator.models import LLMCallLog
from simulator.services.errors import LLMConfigurationError, LLMProviderError

from .base import BaseLLMClient, LLMResponse


class GeminiLLMClient(BaseLLMClient):
    provider = LLMCallLog.PROVIDER_GEMINI

    def __init__(self) -> None:
        self.model = settings.GEMINI_MODEL
        self.api_key = settings.GEMINI_API_KEY
        if not self.api_key:
            raise LLMConfigurationError("GEMINI_API_KEY is required when USE_GEMINI is True.")

    def generate(
        self,
        prompt: str,
        purpose: str,
        system_instruction: Optional[str] = None,
    ) -> LLMResponse:
        prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        request_payload = {
            "prompt": prompt,
            "system_instruction": system_instruction,
            "model": self.model,
        }
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            self._log_failure(purpose, prompt_hash, request_payload, "google-genai is not installed.")
            raise LLMConfigurationError("google-genai is not installed.") from exc

        try:
            client = genai.Client(api_key=self.api_key)
            config = None
            if system_instruction:
                config = types.GenerateContentConfig(system_instruction=system_instruction)
            response = client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=config,
            )
            text = response.text or ""
            raw = {"text": text}
            LLMCallLog.objects.create(
                provider=self.provider,
                model=self.model,
                purpose=purpose,
                prompt_hash=prompt_hash,
                request_payload=request_payload,
                response_payload=raw,
                status=LLMCallLog.STATUS_SUCCESS,
            )
            return LLMResponse(text=text, raw=raw, provider=self.provider, model=self.model)
        except LLMConfigurationError:
            raise
        except Exception as exc:
            self._log_failure(purpose, prompt_hash, request_payload, str(exc))
            raise LLMProviderError(str(exc)) from exc

    def _log_failure(self, purpose: str, prompt_hash: str, request_payload: dict, error_message: str) -> None:
        LLMCallLog.objects.create(
            provider=self.provider,
            model=self.model,
            purpose=purpose,
            prompt_hash=prompt_hash,
            request_payload=request_payload,
            response_payload={},
            status=LLMCallLog.STATUS_FAILED,
            error_message=error_message,
        )

