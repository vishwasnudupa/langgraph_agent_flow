"""
LLM Factory — provides a chat model based on the configured provider.

Keeps token usage moderate by using smaller / flash models by default.
"""
from __future__ import annotations

from functools import lru_cache

from langchain_core.language_models.chat_models import BaseChatModel

from src.core.config import get_settings


@lru_cache(maxsize=4)
def get_llm(
    provider: str | None = None,
    model: str | None = None,
    temperature: float = 0.2,
) -> BaseChatModel:
    """
    Create (and cache) a chat model instance.

    Args:
        provider: "openai", "google", or "anthropic". Falls back to settings.
        model: Override model name. Falls back to settings.
        temperature: Sampling temperature (low = deterministic).
    """
    settings = get_settings()
    provider = provider or settings.llm_provider

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=model or settings.openai_model,
            temperature=temperature,
            api_key=settings.openai_api_key,
            max_tokens=2048,  # medium consumption
        )
    elif provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=model or settings.google_model,
            temperature=temperature,
            google_api_key=settings.google_api_key,
            max_output_tokens=2048,
        )
    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=model or settings.anthropic_model,
            temperature=temperature,
            api_key=settings.anthropic_api_key,
            max_tokens=2048,
        )
    else:
        raise ValueError(f"Unknown LLM provider: {provider!r}. Use openai/google/anthropic.")
