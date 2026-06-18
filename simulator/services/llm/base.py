from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class LLMResponse:
    text: str
    raw: Dict[str, Any]
    provider: str
    model: str


class BaseLLMClient:
    provider = ""
    model = ""

    def generate(
        self,
        prompt: str,
        purpose: str,
        system_instruction: Optional[str] = None,
    ) -> LLMResponse:
        raise NotImplementedError

