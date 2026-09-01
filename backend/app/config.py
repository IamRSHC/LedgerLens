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

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
