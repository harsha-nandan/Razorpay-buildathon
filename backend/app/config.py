from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM provider selection - pluggable, chosen at runtime via env var.
    llm_provider: str = "ollama"  # "anthropic" | "openai" | "ollama" | "groq" | "gemini"
    anthropic_api_key: str | None = None
    anthropic_model_id: str = "claude-sonnet-5"
    openai_api_key: str | None = None
    openai_model_id: str = "gpt-4o-mini"
    # Groq: free tier, no card required, and dramatically faster than local
    # CPU/integrated-GPU inference (runs on Groq's own inference hardware).
    # OpenAI-API-compatible, so it reuses the OpenAI provider with a
    # different base_url instead of needing its own client.
    groq_api_key: str | None = None
    groq_model_id: str = "llama-3.3-70b-versatile"
    groq_base_url: str = "https://api.groq.com/openai/v1"
    # Gemini: also has a genuinely free tier (Google AI Studio, no card
    # required) and is natively supported by Strands.
    gemini_api_key: str | None = None
    gemini_model_id: str = "gemini-2.5-flash"
    ollama_host: str = "http://localhost:11434"
    ollama_model_id: str = "qwen2.5:3b"
    # Number of model layers to offload to GPU, the rest run on CPU (hybrid).
    # Full offload (a large number, or Ollama's "auto") overflows this
    # integrated GPU's tiny Vulkan-allocatable memory pool and errors out on
    # load - a small explicit count instead offloads part of the model
    # without hitting that ceiling. Set to 0 to force pure CPU; raise this a
    # lot (e.g. 999) on a machine with real dedicated VRAM.
    ollama_num_gpu: int = 8

    # Razorpay - defaults to the mock gateway until live test keys are supplied.
    razorpay_mode: str = "mock"  # "mock" | "live"
    razorpay_key_id: str | None = None
    razorpay_key_secret: str | None = None

    database_url: str = "sqlite:///./agentic_commerce.db"

    # Auth - fine as a static dev default for a hackathon demo; override via
    # env for anything longer-lived.
    jwt_secret: str = "dev-secret-change-me-a1b2c3-please-rotate-me"
    jwt_expires_minutes: int = 60 * 24 * 7

    # Merchant growth guardrails enforced by the gatekeeper - hard bounds that
    # can never be overridden by the LLM, regardless of what it argues for.
    max_single_order_paise: int = 5_00_000  # INR 5,000
    max_discount_percent: int = 40
    daily_campaign_budget_paise: int = 20_00_000  # INR 20,000
    max_campaign_recipients: int = 25
    max_orders_per_session: int = 5

    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
