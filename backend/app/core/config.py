from pydantic_settings import BaseSettings
from sqlalchemy import URL


class Settings(BaseSettings):
    db_username: str
    db_password: str
    db_host: str
    db_port: int
    db_database: str

    @property
    def database_url(self) -> URL:
        return URL.create(
            "postgresql+psycopg",
            username=self.db_username,
            password=self.db_password,
            host=self.db_host,
            port=self.db_port,
            database=self.db_database,
        )

    jwt_secret_key: str
    access_token_minutes: int = 15
    refresh_token_days: int = 7
    auth_cookie_secure: bool = False
    auth_allowed_origins: list[str]
    # Zona horaria para saber qué día es hoy (por ejemplo, para la campaña actual)
    app_timezone: str = "America/Argentina/Mendoza"


settings = Settings()
