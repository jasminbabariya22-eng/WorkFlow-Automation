from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    WORKFLOW_DATABASE_URL: str = "postgresql+psycopg2://postgres:Alethe%40123@192.168.1.171:5432/workflow_erm"
    WORKFLOW_DB_SCHEMA: str = "workflow"
    DATABASE_URL: Optional[str] = None
    DB_SCHEMA: Optional[str] = "workflow"

    SECRET_KEY: str = "0eeedb8821a0a275fc8afb816145a44cee60bfc7f55f51b1f091cca47596cdb0"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    FERNET_KEY: Optional[str] = "ia3rsWe2JkwStfuoRIOdDtsghWrDuFY02l5tR-XyCIc="
    MAIN_URL: Optional[str] = "http://localhost:3000"

    class Config:
        env_file = ".env"
        extra = "ignore"

    def __init__(self, **values):
        super().__init__(**values)
        if not self.DATABASE_URL:
            self.DATABASE_URL = self.WORKFLOW_DATABASE_URL


settings = Settings()