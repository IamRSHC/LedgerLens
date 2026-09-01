from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "sqlite:///./ledgerlens.db"
    groq_api_key: str = ""
    environment: str = "development"
    frontend_url: str = "http://localhost:3000"

    # Step 1.7: single authoritative auto-resolution confidence threshold.
    # Consumed by `classifier.should_auto_resolve`. Frontend must NOT re-derive
    # this — it consumes the backend's `investigation.auto_resolved` decision.
    # Optional env override: AUTO_RESOLVE_CONFIDENCE=0.90
    auto_resolve_confidence: float = 0.85

    # Step 6.1: Groq live-path configuration. All optional — sensible defaults
    # keep the demo working without a .env change. The API key comes ONLY from
    # env; it is never hard-coded and never logged/echoed.
    groq_model:       str = "llama-3.3-70b-versatile"
    groq_max_rounds:  int = 5     # LLM turns per investigation
    groq_max_tokens:  int = 1000  # completion cap per LLM call

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
