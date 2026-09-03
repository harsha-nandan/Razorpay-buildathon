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

from ..config import Settings, get_settings


class LLMNotConfiguredError(RuntimeError):
    """Raised when the selected provider has no API key set yet, or (for
    ollama) isn't reachable."""


def _build_anthropic_model(settings: Settings) -> Model:
    from strands.models.anthropic import AnthropicModel

    client_args: dict = {"api_key": settings.anthropic_api_key}
    if settings.anthropic_workspace_id:
        # Required for an identity-linked API key (tied to a person across
        # an org with multiple workspaces) - Anthropic rejects requests from
        # one of these with 400 "anthropic-workspace-id is required" unless
        # every request carries this header.
        client_args["default_headers"] = {"anthropic-workspace-id": settings.anthropic_workspace_id}

    return AnthropicModel(
        client_args=client_args,
        model_id=settings.anthropic_model_id,
        max_tokens=2048,
    )


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
        groq_keys = settings.groq_api_keys
        if not groq_keys:
            raise LLMNotConfiguredError(
                "LLM_PROVIDER=groq but no GROQ_API_KEY is set. Get a free key at "
                "https://console.groq.com/keys and add it to backend/.env."
            )
        from strands.models.openai import OpenAIModel

        from .fallback_model import FallbackModel

        # Groq's API is OpenAI-compatible, so the OpenAI provider works
        # unmodified against Groq's endpoint - no separate client needed.
        groq_models = [
            OpenAIModel(client_args={"api_key": key, "base_url": settings.groq_base_url}, model_id=settings.groq_model_id)
            for key in groq_keys
        ]

        # Each Groq key has its own daily token cap that runs out on its
        # own. Chain the configured keys together with FallbackModel so a
        # throttle on key N rotates to key N+1 - identified only by index in
        # logs, never by value - before anything falls through to Anthropic.
        # Built right-to-left so the last key's fallback is Anthropic (or
        # nothing) and each earlier key's fallback is that chain.
        model: Model = groq_models[-1]
        for key_index in range(len(groq_models) - 1, 0, -1):
            model = FallbackModel(
                groq_models[key_index - 1],
                model,
                primary_name=f"groq-key-{key_index}",
                fallback_name=f"groq-key-{key_index + 1}",
            )

        # Groq's free tier runs out - rather than the whole app going dark
        # until someone notices and flips LLM_PROVIDER by hand, fail over to
        # Anthropic automatically once every Groq key is throttled, if a key
        # is available.
        if settings.anthropic_api_key:
            model = FallbackModel(
                model,
                _build_anthropic_model(settings),
                primary_name=f"groq (keys 1-{len(groq_models)})",
                fallback_name="anthropic",
            )
        return model

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
        return _build_anthropic_model(settings)

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
        return bool(settings.groq_api_keys)
    if provider == "gemini":
        return bool(settings.gemini_api_key)
    if provider == "ollama":
        return bool(settings.ollama_host)
    return False
