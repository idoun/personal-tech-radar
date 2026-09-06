from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from app.core.config import DEFAULT_DATABASE_PATH, PROJECT_ROOT, settings


SQLITE_URL_PREFIX = 'sqlite:///'


def test_default_database_path_points_to_project_root_db():
    assert DEFAULT_DATABASE_PATH == PROJECT_ROOT / 'technews.db'


def test_settings_database_path_resolves_absolute_sqlite_path():
    configured_path = Path(settings.database_url.removeprefix(SQLITE_URL_PREFIX))

    assert settings.database_path == configured_path.resolve()
    assert settings.database_path.is_absolute()
