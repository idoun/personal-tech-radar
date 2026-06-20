from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from app.core.issue_analysis import parse_issue_markdown


def test_parse_issue_markdown_supports_per_article_community_reaction():
    markdown = """오늘의 흐름: 요약입니다.

## 기사 A
요약: 본문입니다.
- 댓글 반응: 댓글에서는 운영 복잡도를 더 많이 따진다는 반응이 보임.
- 댓글 포인트: 도입보다 유지보수가 더 어렵다는 의견이 있었음.
- 댓글 포인트: 팀 공용 규칙과 개인 설정을 분리해야 한다는 얘기도 나옴.
- 원문: https://example.com/a
- GeekNews: https://news.hada.io/topic?id=1
"""

    parsed = parse_issue_markdown(markdown)

    assert len(parsed.cards) == 1
    assert parsed.cards[0].community_reaction == '댓글에서는 운영 복잡도를 더 많이 따진다는 반응이 보임.'
    assert parsed.cards[0].community_points == [
        '도입보다 유지보수가 더 어렵다는 의견이 있었음.',
        '팀 공용 규칙과 개인 설정을 분리해야 한다는 얘기도 나옴.',
    ]
