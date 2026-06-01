#!/usr/bin/env python3
import json
import os
import sqlite3
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
CONTENT_ROOT = WORKSPACE / 'content'
DB_PATH = ROOT / 'backend' / 'technews.db'


def main():
    payload = json.load(sys.stdin)
    issue_date = payload['issue_date']
    title = payload['title']
    summary = payload['summary']
    markdown = payload['markdown'].strip() + '\n'
    slug = payload.get('slug') or issue_date
    y, m, _ = issue_date.split('-')
    rel_path = f'{y}/{m}/{slug}-geeknews.md'
    content_path = CONTENT_ROOT / rel_path
    content_path.parent.mkdir(parents=True, exist_ok=True)
    content_path.write_text(markdown, encoding='utf-8')

    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        '''INSERT INTO issues (slug, title, summary, issue_date, year, month, markdown_path, is_published, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, 1, datetime('now'), datetime('now'))
           ON CONFLICT(slug) DO UPDATE SET
             title=excluded.title,
             summary=excluded.summary,
             issue_date=excluded.issue_date,
             year=excluded.year,
             month=excluded.month,
             markdown_path=excluded.markdown_path,
             is_published=1,
             updated_at=datetime('now')''',
        (slug, title, summary, issue_date, int(y), int(m), rel_path),
    )
    conn.commit()
    conn.close()
    print(json.dumps({'ok': True, 'slug': slug, 'markdown_path': rel_path}, ensure_ascii=False))


if __name__ == '__main__':
    main()
