from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from app.core.config import settings


def test_content_root_points_to_workspace_content_dir():
    assert settings.content_root_path == Path('/home/ubuntu/.openclaw/workspace/content')


def test_database_path_points_to_project_root_db():
    assert settings.database_path == Path('/home/ubuntu/.openclaw/workspace/technews-publisher/technews.db')
