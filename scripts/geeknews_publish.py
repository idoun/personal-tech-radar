#!/usr/bin/env python3
import json
import sys
from datetime import UTC, datetime, timedelta

from ingest_issue import main as ingest_main  # type: ignore


def build_issue_date(now: datetime) -> str:
    return (now.date() - timedelta(days=1)).isoformat()


def extract_summary(markdown: str) -> str:
    for line in markdown.splitlines():
        line = line.strip()
        if line.startswith('오늘의 흐름:'):
            return line.replace('오늘의 흐름:', '', 1).strip()
    return 'GeekNews 요약 아카이브'



def build_title(issue_date: str) -> str:
    return f'GeekNews 어제자 요약 - {issue_date}'


def main():
    markdown = sys.stdin.read().strip()
    if not markdown:
        raise SystemExit('No markdown input received')

    now = datetime.now(UTC) + timedelta(hours=9)
    issue_date = build_issue_date(now)
    summary = extract_summary(markdown)
    payload = {
        'issue_date': issue_date,
        'title': build_title(issue_date),
        'summary': summary,
        'markdown': markdown,
    }

    original_stdin = sys.stdin
    try:
        sys.stdin = type('InMemoryStdin', (), {'read': lambda self='': json.dumps(payload, ensure_ascii=False)})()
        ingest_main()
    finally:
        sys.stdin = original_stdin


if __name__ == '__main__':
    main()
