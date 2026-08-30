from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "sqlite:///./ledgerlens.db"
    groq_api_key: str = ""
    environment: str = "development"
    frontend_url: str = "http://localhost:3000"
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
