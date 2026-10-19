from decimal import Decimal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/minimarket"
    jwt_secret: str = "cambiar-en-produccion"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 720
    costo_envio: Decimal = Decimal("1.50")

    # URL base de la API (para generar enlaces de verificación en correos)
    api_base_url: str = "http://localhost:8000"

    # Configuración de Correo SMTP (Gmail u otros)
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 465
    smtp_user: str = ""
    smtp_password: str = ""
    email_verification_token_expire_hours: int = 24


settings = Settings()