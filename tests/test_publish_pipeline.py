from pathlib import Path
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
