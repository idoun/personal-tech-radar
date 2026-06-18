from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


WORKSPACE_ROOT = Path(__file__).resolve().parents[4]
PROJECT_ROOT = WORKSPACE_ROOT / 'technews-publisher'
DEFAULT_DATABASE_PATH = PROJECT_ROOT / 'technews.db'


class Settings(BaseSettings):
    app_name: str = 'Personal Tech Radar API'
    app_env: str = 'development'
    database_url: str = f'sqlite:///{DEFAULT_DATABASE_PATH}'
    content_root: str = '../content'
    ingest_token: str = ''
    auth_secret_key: str = ''
    auth_cookie_name: str = 'idounai_session'
    tech_radar_profile_path: str = 'config/tech-radar-profile.yaml'
    tech_radar_min_telegram_score: float = 7.0
    tech_radar_important_score: float = 8.5

    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')

    @property
    def content_root_path(self) -> Path:
        return (PROJECT_ROOT / self.content_root).resolve()

    @property
    def database_path(self) -> Path:
        prefix = 'sqlite:///'
        if self.database_url.startswith(prefix):
            return Path(self.database_url[len(prefix):]).resolve()
        raise ValueError('Only sqlite database_url is supported for local path resolution')


settings = Settings()
