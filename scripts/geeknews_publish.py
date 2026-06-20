#!/usr/bin/env python3
import json
import os
import re
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_VENV = PROJECT_ROOT / 'backend' / '.venv'
BACKEND_VENV_PYTHON = BACKEND_VENV / 'bin' / 'python'
REEXEC_GUARD = 'TECHNEWS_GEEKNEWS_PUBLISH_REEXEC'


def ensure_backend_venv_python() -> None:
    current_prefix = Path(sys.prefix).resolve()
    if current_prefix == BACKEND_VENV.resolve():
        return
    if os.environ.get(REEXEC_GUARD) == '1':
        return
    if not BACKEND_VENV_PYTHON.exists():
        return

    env = os.environ.copy()
    env[REEXEC_GUARD] = '1'
    os.execve(
        str(BACKEND_VENV_PYTHON),
        [str(BACKEND_VENV_PYTHON), str(Path(__file__).resolve())],
        env,
    )


def build_issue_date(now: datetime) -> str:
    return (now.date() - timedelta(days=1)).isoformat()


def extract_summary(markdown: str) -> str:
    for line in markdown.splitlines():
        line = line.strip()
        if line.startswith('오늘의 흐름:'):
            return line.replace('오늘의 흐름:', '', 1).strip()
    return 'GeekNews 요약 아카이브'


COMMUNITY_REACTION_HEADINGS = {
    '커뮤니티 반응',
    '댓글에서 나온 포인트',
}


def _normalize_heading_text(line: str) -> str:
    text = re.sub(r'^\s*#+\s*', '', line).strip()
    text = re.sub(r'[*_`]+', '', text).strip()
    return text


def extract_community_reaction(markdown: str) -> tuple[str, list[str], str]:
    lines = markdown.splitlines()
    start_index: int | None = None
    end_index = len(lines)

    for index, raw_line in enumerate(lines):
        if _normalize_heading_text(raw_line) in COMMUNITY_REACTION_HEADINGS:
            start_index = index
            break

    if start_index is None:
        return '', [], markdown

    for index in range(start_index + 1, len(lines)):
        if re.match(r'^\s*##+\s+', lines[index]):
            end_index = index
            break

    summary_parts: list[str] = []
    bullets: list[str] = []
    for raw_line in lines[start_index + 1 : end_index]:
        line = raw_line.strip()
        if not line:
            continue
        if re.match(r'^[-*•]\s+', line):
            bullet = re.sub(r'^[-*•]\s+', '', line).strip()
            if bullet:
                bullets.append(bullet)
            continue
        if line.lower().startswith('요약:'):
            line = line.split(':', 1)[1].strip()
        if line:
            summary_parts.append(line)

    cleaned_lines = lines[:start_index]
    if cleaned_lines and end_index < len(lines) and cleaned_lines[-1].strip():
        cleaned_lines.append('')
    cleaned_lines.extend(lines[end_index:])
    cleaned_markdown = '\n'.join(cleaned_lines).strip()

    return ' '.join(summary_parts).strip()[:160], bullets[:2], cleaned_markdown



def build_title(issue_date: str) -> str:
    return f'GeekNews 어제자 요약 - {issue_date}'


def main():
    ensure_backend_venv_python()
    from ingest_issue import main as ingest_main  # type: ignore

    markdown = sys.stdin.read().strip()
    if not markdown:
        raise SystemExit('No markdown input received')
    community_reaction_summary, community_reaction_bullets, cleaned_markdown = extract_community_reaction(markdown)

    now = datetime.now(UTC) + timedelta(hours=9)
    issue_date = build_issue_date(now)
    summary = extract_summary(cleaned_markdown)
    payload = {
        'issue_date': issue_date,
        'title': build_title(issue_date),
        'summary': summary,
        'markdown': cleaned_markdown,
        'community_reaction_summary': community_reaction_summary,
        'community_reaction_bullets': community_reaction_bullets,
    }

    original_stdin = sys.stdin
    try:
        sys.stdin = type('InMemoryStdin', (), {'read': lambda self='': json.dumps(payload, ensure_ascii=False)})()
        ingest_main()
    finally:
        sys.stdin = original_stdin


if __name__ == '__main__':
    main()
