from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from app.core.article_keys import build_article_key, normalize_article_title


def test_normalize_article_title_handles_korean_and_symbols():
    assert normalize_article_title(' Git에서 파일을 무시하는 방법은 .gitignore만이 아님! ') == 'git에서-파일을-무시하는-방법은-gitignore만이-아님'


def test_build_article_key_appends_issue_slug_and_index():
    assert build_article_key('2026-06-19', 'SQLite의 창시자 이야기', 2) == '2026-06-19::sqlite의-창시자-이야기::2'
