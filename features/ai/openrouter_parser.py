"""OpenRouter fallback provider factory."""
from __future__ import annotations

from features.ai.openai_compatible_parser import OpenAICompatibleTextParser


# 2026-07-31: z-ai/glm-5.2를 기본 모델로 올림 (Hermes와 동일).
# 기존 llama-3.1-8b:free는 404 단종 가능성이 있어 fallback으로 보류.
_DEFAULT_MODEL = "z-ai/glm-5.2"
_FALLBACK_MODEL = "meta-llama/llama-3.1-8b-instruct:free"


def create_openrouter_parser(
    api_key: str,
    model: str = _DEFAULT_MODEL,
):
    # sk-or-v1 키면 OpenRouter 직접 호출 (z.ai 직접 키가 아님)
    return OpenAICompatibleTextParser(
        provider_name="openrouter",
        base_url="https://openrouter.ai/api/v1",
        model=model or _DEFAULT_MODEL,
        api_key=api_key,
    )

