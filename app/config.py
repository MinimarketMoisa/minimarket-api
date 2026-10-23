import secrets
from decimal import Decimal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    entorno: str = "produccion"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/minimarket"
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    costo_envio: Decimal = Decimal("1.50")
    cors_origins: list[str] = []

    # Password reset
    password_reset_token_expire_minutes: int = 30
    frontend_reset_url: str = ""

    # URL base de la API (para generar enlaces de verificación en correos)
    api_base_url: str = "http://localhost:8000"
    enable_docs: bool = True

    # Configuración de Correo SMTP (Gmail u otros)
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 465
    smtp_user: str = ""
    smtp_password: str = ""
    email_verification_token_expire_hours: int = 24

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return []
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [x.strip() for x in v.split(",") if x.strip()]
        return v or []

    @model_validator(mode="after")
    def _validar(self):
        if self.jwt_algorithm not in {"HS256", "HS384", "HS512"}:
            raise ValueError("jwt_algorithm inválido")
        if self.entorno == "produccion":
            if len(self.jwt_secret) < 32:
                raise ValueError("JWT_SECRET debe tener 32+ caracteres en producción")
            if "postgres:postgres@" in self.database_url:
                raise ValueError("Cambia las credenciales por defecto de la BD")
            if not self.api_base_url.startswith("https://"):
                raise ValueError("API_BASE_URL debe ser https en producción")
        elif not self.jwt_secret:
            self.jwt_secret = secrets.token_urlsafe(64)
        return self


settings = Settings()
