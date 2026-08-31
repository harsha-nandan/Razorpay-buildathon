"""Pluggable model provider for every Strands agent in this app.

Swapping LLM_PROVIDER in .env (anthropic <-> openai <-> ollama <-> groq <->
gemini) changes the brain behind every agent - the conversational checkout
agent, the campaign orchestrator, the AI buyer, and the LLM-gatekeeper -
without touching agent code. ollama is the default: it runs entirely on the
local machine against an already-running `ollama serve`, so the whole app
works end to end with zero API keys and zero external calls. groq and
gemini are both genuinely free (no card required) if local inference is too
slow on your hardware - groq in particular runs on dedicated inference
hardware and is dramatically faster than CPU/integrated-GPU Ollama.
"""

from functools import lru_cache

from strands.models.model import Model

from ..config import get_settings


class LLMNotConfiguredError(RuntimeError):
    """Raised when the selected provider has no API key set yet, or (for
    ollama) isn't reachable."""


@lru_cache
def get_model() -> Model:
    settings = get_settings()
    provider = settings.llm_provider.lower()

    if provider == "ollama":
        from strands.models.ollama import OllamaModel

        return OllamaModel(
            settings.ollama_host,
            model_id=settings.ollama_model_id,
            options={"num_gpu": settings.ollama_num_gpu},
        )

    if provider == "groq":
        if not settings.groq_api_key:
            raise LLMNotConfiguredError(
                "LLM_PROVIDER=groq but GROQ_API_KEY is not set. Get a free key at "
                "https://console.groq.com/keys and add it to backend/.env."
            )
        from strands.models.openai import OpenAIModel

        # Groq's API is OpenAI-compatible, so the OpenAI provider works
        # unmodified against Groq's endpoint - no separate client needed.
        return OpenAIModel(
            client_args={"api_key": settings.groq_api_key, "base_url": settings.groq_base_url},
            model_id=settings.groq_model_id,
        )

    if provider == "gemini":
        if not settings.gemini_api_key:
            raise LLMNotConfiguredError(
                "LLM_PROVIDER=gemini but GEMINI_API_KEY is not set. Get a free key at "
                "https://aistudio.google.com/apikey and add it to backend/.env."
            )
        from strands.models.gemini import GeminiModel

        return GeminiModel(
            client_args={"api_key": settings.gemini_api_key},
            model_id=settings.gemini_model_id,
        )

    if provider == "openai":
        if not settings.openai_api_key:
            raise LLMNotConfiguredError(
                "LLM_PROVIDER=openai but OPENAI_API_KEY is not set. Add it to backend/.env."
            )
        from strands.models.openai import OpenAIModel

        return OpenAIModel(
            client_args={"api_key": settings.openai_api_key},
            model_id=settings.openai_model_id,
        )

    if provider == "anthropic":
        if not settings.anthropic_api_key:
            raise LLMNotConfiguredError(
                "LLM_PROVIDER=anthropic but ANTHROPIC_API_KEY is not set. Add it to backend/.env."
            )
        from strands.models.anthropic import AnthropicModel

        return AnthropicModel(
            client_args={"api_key": settings.anthropic_api_key},
            model_id=settings.anthropic_model_id,
            max_tokens=2048,
        )

    raise ValueError(
        f"Unknown LLM_PROVIDER '{settings.llm_provider}'. Use 'anthropic', 'openai', 'ollama', 'groq', or 'gemini'."
    )


def is_llm_configured() -> bool:
    settings = get_settings()
    provider = settings.llm_provider.lower()
    if provider == "openai":
        return bool(settings.openai_api_key)
    if provider == "anthropic":
        return bool(settings.anthropic_api_key)
    if provider == "groq":
        return bool(settings.groq_api_key)
    if provider == "gemini":
        return bool(settings.gemini_api_key)
    if provider == "ollama":
        return bool(settings.ollama_host)
    return False
