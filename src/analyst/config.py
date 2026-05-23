from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Typed, env-backed application settings.

    Loads from `.env` (and process env) once at import via the module-level
    `settings = Settings()`. Fails fast: missing `OPENAI_API_KEY` raises at
    import time, which is what we want — secrets and required config should
    never be discovered lazily mid-request.

    Demonstrates: pydantic-settings as the "boundary validator" for external
    configuration, per CLAUDE.md §5. Keys are env-only; nothing here is committed.
    """
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    OPENAI_API_KEY: str = Field(min_length=1)
    DEFAULT_MODEL: str = "openai:gpt-4o-mini"
    DEFAULT_TEMPERATURE: float = 0.0

settings = Settings()
