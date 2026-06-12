from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from app.core.config import DEFAULT_DATABASE_PATH, PROJECT_ROOT, settings


def test_default_database_path_points_to_project_root_db():
    assert DEFAULT_DATABASE_PATH == PROJECT_ROOT / 'technews.db'


def test_settings_database_path_resolves_absolute_sqlite_path():
    assert settings.database_path == Path('/home/ubuntu/.openclaw/workspace/technews-publisher/technews.db')
