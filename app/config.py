from decimal import Decimal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/minimarket"
    jwt_secret: str = "cambiar-en-produccion"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 720
    costo_envio: Decimal = Decimal("1.50")


settings = Settings()
