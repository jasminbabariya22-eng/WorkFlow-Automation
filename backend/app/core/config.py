from pathlib import Path
from typing import Optional
from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

# Determine project base directory for reliable .env discovery
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
_ENV_PATH = _BACKEND_DIR / ".env"

class Settings(BaseSettings):
    # Primary Workflow Engine Database (Required from environment or .env)
    WORKFLOW_DATABASE_URL: str = Field(
        ...,
        description="Database connection URI for the workflow engine."
    )
    WORKFLOW_DB_SCHEMA: str = "workflow"

    # Security, JWT & Encryption (Required from environment or .env)
    SECRET_KEY: str = Field(
        ...,
        description="Secret key used for signing and verifying JWT authentication tokens."
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    FERNET_KEY: str = Field(
        ...,
        description="Symmetric encryption key used for sensitive credential storage."
    )
    MAIN_URL: Optional[str] = "http://localhost:3000"

    model_config = SettingsConfigDict(
        env_file=(".env", str(_ENV_PATH)),
        env_file_encoding="utf-8",
        extra="ignore"
    )


def load_settings() -> Settings:
    """
    Instantiates and validates the application settings.
    Raises a clean, non-sensitive RuntimeError if any required secrets are missing,
    without printing any secret values in the logs or terminal.
    """
    try:
        return Settings()
    except ValidationError as e:
        missing_fields = []
        for err in e.errors():
            if "missing" in str(err.get("type", "")):
                loc = ".".join(str(part) for part in err.get("loc", []))
                missing_fields.append(loc)

        if missing_fields:
            missing_str = ", ".join(missing_fields)
            raise RuntimeError(
                f"Application configuration error: The following required environment variables are missing: [{missing_str}]. "
                "Please configure them in your environment or .env file before starting the server."
            ) from None
        raise RuntimeError(
            f"Application configuration validation failed: {len(e.errors())} error(s) detected. "
            "Please check your environment configuration."
        ) from None


settings = load_settings()
