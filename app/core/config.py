# App configuration file
# app/core/config.py
from pydantic_settings import BaseSettings
from pydantic import Field, AnyUrl

class Settings(BaseSettings):
    # App
    APP_ENV: str = Field(default="dev", description="Environment name: dev|test|prod")
    API_PREFIX: str = Field(default="/api", description="Base prefix for API routes")
    DEBUG: bool = Field(default=True)

    # PostgreSQL (por ahora aceptamos DSN sync o async; en el Paso 3 la haremos async)
    # Ej: postgresql+psycopg://user:pass@localhost:5432/healthcare_db
    SQL_DSN: str = Field(default="", description="SQLAlchemy DSN for PostgreSQL")

    # Pool / Engine (usaremos estos en el Paso 3)
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_ECHO: bool = False

    # Auth (los usaremos cuando implementemos login/register tokens)
    JWT_SECRET: str = Field(default="change_me", description="Only for dev")
    ACCESS_EXPIRES_MIN: int = 60
    REFRESH_EXPIRES_DAYS: int = 7

    class Config:
        env_file = ".env"
        extra = "ignore"  # ignora variables que no estén definidas

settings = Settings()
