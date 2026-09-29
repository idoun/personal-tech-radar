#!/usr/bin/env python3
"""Publish a prepared ByteByteGo summary without copying the source email."""

import argparse
import json
import sqlite3
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))

from app.core.config import settings


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--issue-date', required=True, help='Publisher date in YYYY-MM-DD')
    args = parser.parse_args()

    issue_date = date.fromisoformat(args.issue_date)

    slug = f'bytebytego-{issue_date.isoformat()}'
    with sqlite3.connect(settings.database_path) as db:
        if db.execute('SELECT 1 FROM issues WHERE slug = ?', (slug,)).fetchone():
            print(json.dumps({'ok': True, 'slug': slug, 'skipped': 'already_exists'}))
            return

    markdown = sys.stdin.read().strip()
    lines = markdown.splitlines()
    if not lines or not lines[0].startswith('이번 호의 흐름:') or markdown.count('\n## ') < 2:
        parser.error('expected a Korean issue summary and at least two article sections')

    payload = {
        'issue_date': issue_date.isoformat(),
        'source': 'bytebytego',
        'title': f'ByteByteGo 주간 요약 - {issue_date.isoformat()}',
        'summary': lines[0],
        'tags': ['ByteByteGo'],
        'markdown': markdown,
    }
    completed = subprocess.run(
        [sys.executable, str(ROOT / 'scripts' / 'ingest_issue.py')],
        input=json.dumps(payload, ensure_ascii=False), text=True, capture_output=True, check=True,
    )
    print(completed.stdout.strip())


if __name__ == '__main__':
    main()
