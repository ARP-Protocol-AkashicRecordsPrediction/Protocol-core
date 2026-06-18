import json
from typing import Any, Dict, Iterable, List

from .errors import LLMJSONParseError


def _strip_code_fence(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    return cleaned


def _extract_between(text: str, start_char: str, end_char: str) -> str:
    cleaned = _strip_code_fence(text)
    start = cleaned.find(start_char)
    end = cleaned.rfind(end_char)
    if start == -1 or end == -1 or end < start:
        raise LLMJSONParseError("LLM response did not contain JSON.")
    return cleaned[start : end + 1]


def extract_json_object(text: str) -> Dict[str, Any]:
    raw = _extract_between(text, "{", "}")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LLMJSONParseError(str(exc)) from exc
    if not isinstance(data, dict):
        raise LLMJSONParseError("Expected a JSON object.")
    return data


def extract_json_array(text: str) -> List[Any]:
    raw = _extract_between(text, "[", "]")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LLMJSONParseError(str(exc)) from exc
    if not isinstance(data, list):
        raise LLMJSONParseError("Expected a JSON array.")
    return data


def require_keys(data: Dict[str, Any], keys: Iterable[str]) -> None:
    missing = [key for key in keys if key not in data]
    if missing:
        raise LLMJSONParseError("Missing required keys: " + ", ".join(missing))


def coerce_float_score(value: Any, field_name: str) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError) as exc:
        raise LLMJSONParseError(f"{field_name} must be a number.") from exc
    if score < 0 or score > 1:
        raise LLMJSONParseError(f"{field_name} must be between 0 and 1.")
    return score

