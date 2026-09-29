from pathlib import Path
import json
import os
import sqlite3
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

from geeknews_publish import extract_community_reaction
from ingest_issue import _normalize_community_reaction


def test_extract_community_reaction_removes_section_from_markdown():
    markdown = """오늘의 흐름: 요약입니다.

## 기사 A
요약: 본문입니다.

## 커뮤니티 반응
요약: 댓글에서는 도입 난이도보다 실제 운영에서 유지 비용이 더 중요하다는 반응이 많았음.
- 벤치마크보다 운영 안정성이 더 중요하다는 의견이 보였음.
- 장애 대응 경험이 핵심이라는 반응도 있었음.

## 기사 B
요약: 다음 본문입니다.
"""

    summary, bullets, cleaned_markdown = extract_community_reaction(markdown)

    assert summary == '댓글에서는 도입 난이도보다 실제 운영에서 유지 비용이 더 중요하다는 반응이 많았음.'
    assert bullets == [
        '벤치마크보다 운영 안정성이 더 중요하다는 의견이 보였음.',
        '장애 대응 경험이 핵심이라는 반응도 있었음.',
    ]
    assert '## 커뮤니티 반응' not in cleaned_markdown
    assert '## 기사 A' in cleaned_markdown
    assert '## 기사 B' in cleaned_markdown


def test_normalize_community_reaction_caps_summary_and_bullets():
    summary, bullets = _normalize_community_reaction(
        {
            'community_reaction_summary': '가' * 200,
            'community_reaction_bullets': ['첫째', '', '둘째', '셋째'],
        }
    )

    assert len(summary) == 160
    assert bullets == ['첫째', '둘째']


def test_bytebytego_issue_uses_a_distinct_slug_and_upserts(tmp_path):
    db_path = tmp_path / 'technews.db'
    content_root = tmp_path / 'content'
    env = {
        **os.environ,
        'DATABASE_URL': f'sqlite:///{db_path}',
        'CONTENT_ROOT': str(content_root),
    }
    subprocess.run(
        [sys.executable, '-c', 'from app.main import ensure_tables; ensure_tables()'],
        cwd=ROOT / 'backend', env=env, check=True, capture_output=True, text=True,
    )

    payload = {
        'issue_date': '2026-09-26',
        'source': 'bytebytego',
        'source_url': 'https://newsletter.bytebytego.com/p/nonfunctional-link',
        'title': 'ByteByteGo 주간 요약',
        'summary': '시스템 설계 주간 요약',
        'markdown': '이번 호의 흐름: 설계 기초.\n\n## API 설계\n요약: 계약을 명확히 한다.\n',
    }
    for _ in range(2):
        result = subprocess.run(
            [sys.executable, str(ROOT / 'scripts' / 'ingest_issue.py')],
            input=json.dumps(payload, ensure_ascii=False),
            env=env, check=True, capture_output=True, text=True,
        )
        assert json.loads(result.stdout)['slug'] == 'bytebytego-2026-09-26'

    with sqlite3.connect(db_path) as db:
        rows = db.execute(
            "SELECT slug, source, source_url, markdown_path FROM issues WHERE source = 'bytebytego'"
        ).fetchall()
    assert rows == [(
        'bytebytego-2026-09-26', 'bytebytego', None,
        '2026/09/bytebytego-2026-09-26.md',
    )]
    assert (content_root / rows[0][3]).exists()

    prepared = '이번 호의 흐름: API 설계.\n\n## 계약\n요약: 명확히 한다.\n\n## 오류\n요약: 일관되게 다룬다.\n'
    publisher = [
        sys.executable, str(ROOT / 'scripts' / 'bytebytego_publish.py'),
        '--issue-date', '2026-09-26',
    ]
    skipped = subprocess.run(publisher, input=prepared, env=env, check=True, capture_output=True, text=True)
    assert json.loads(skipped.stdout)['skipped'] == 'already_exists'

    publisher[3] = '2026-10-03'
    created = subprocess.run(publisher, input=prepared, env=env, check=True, capture_output=True, text=True)
    assert json.loads(created.stdout)['slug'] == 'bytebytego-2026-10-03'
    with sqlite3.connect(db_path) as db:
        assert db.execute("SELECT count(*) FROM issues WHERE source = 'bytebytego'").fetchone()[0] == 2
