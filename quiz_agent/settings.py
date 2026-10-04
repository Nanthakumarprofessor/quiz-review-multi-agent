# settings.py
import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    HOST: str = "0.0.0.0"
    PORT: int = 8001

    DATABASE_URL: str = "postgresql://postgres:password@localhost:5433/quiz_db"

    # LLM Provider: 'ollama' or 'bedrock'
    LLM_PROVIDER: str = "ollama"

    # Ollama settings
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.1:latest"

    # AWS Bedrock settings
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    BEDROCK_MODEL_ID: str = "anthropic.claude-3-haiku-20240307-v1:0"

    TEMPERATURE: float = 0.3
    MAX_TOKENS: int = 2048
    LOG_LEVEL: str = "INFO"

    @property
    def host(self) -> str:
        return self.HOST

    @property
    def port(self) -> int:
        return self.PORT

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(__file__), ".env"),
        extra="ignore"
    )


settings = Settings()
