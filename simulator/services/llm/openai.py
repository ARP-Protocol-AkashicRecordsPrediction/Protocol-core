import hashlib
from typing import Optional

from django.conf import settings

from simulator.models import LLMCallLog
from simulator.services.errors import LLMConfigurationError, LLMProviderError

from .base import BaseLLMClient, LLMResponse


class OpenAILLMClient(BaseLLMClient):
    provider = LLMCallLog.PROVIDER_OPENAI

    def __init__(self) -> None:
        self.model = settings.OPENAI_MODEL
        self.api_key = settings.OPENAI_API_KEY
        if not self.api_key:
            raise LLMConfigurationError("OPENAI_API_KEY is required when USE_GEMINI is False.")

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
            from openai import OpenAI
        except ImportError as exc:
            self._log_failure(purpose, prompt_hash, request_payload, "openai is not installed.")
            raise LLMConfigurationError("openai is not installed.") from exc

        try:
            client = OpenAI(api_key=self.api_key)
            input_messages = []
            if system_instruction:
                input_messages.append({"role": "system", "content": system_instruction})
            input_messages.append({"role": "user", "content": prompt})
            response = client.responses.create(
                model=self.model,
                input=input_messages,
            )
            text = getattr(response, "output_text", "") or ""
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

