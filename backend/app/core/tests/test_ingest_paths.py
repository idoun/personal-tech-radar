from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from app.core.config import PROJECT_ROOT, settings


def test_content_root_resolves_configured_path():
    configured_path = Path(settings.content_root)
    expected_path = configured_path if configured_path.is_absolute() else PROJECT_ROOT / configured_path

    assert settings.content_root_path == expected_path.resolve()


def test_database_path_resolves_configured_sqlite_url():
    configured_path = Path(settings.database_url.removeprefix('sqlite:///'))

    assert settings.database_path == configured_path.resolve()
