from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = 'TechNews Publisher API'
    app_env: str = 'development'
    database_url: str = 'sqlite:///./technews.db'
    content_root: str = '../content'
    ingest_token: str = ''

    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')

    @property
    def content_root_path(self) -> Path:
        return (Path(__file__).resolve().parents[3] / self.content_root).resolve()


settings = Settings()
