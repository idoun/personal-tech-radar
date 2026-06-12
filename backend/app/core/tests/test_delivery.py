from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from app.core.delivery import build_delivery_preview, evaluate_delivery
from app.schemas.issue import IssueDetail, IssueScore


def build_issue(score: float) -> IssueDetail:
    return IssueDetail(
        id=1,
        slug='2026-06-08',
        title='Agent observability article',
        summary='legacy summary',
        short_summary='에이전트 관찰성 도구 소개',
        impact_summary='현재 프로젝트에서 replay/logging 구조 참고 가능',
        action_items=['schema 비교', '로그 포맷 검토'],
        tags=['GeekNews', 'AI Systems'],
        radar_category='AI Systems',
        radar_status='Trial',
        score=IssueScore(
            interest_score=8.0,
            project_score=8.0,
            novelty_score=6.0,
            actionability_score=7.0,
            credibility_score=6.0,
            community_score=5.0,
            final_score=score,
            reason='Observability and Replay Toolkit과 관련성이 높음',
            recommended_action='schema 비교',
        ),
        issue_date='2026-06-08',
        year=2026,
        month=6,
        is_published=True,
        markdown='x',
        html='x',
        markdown_path='2026/06/x.md',
    )


def test_evaluate_delivery_thresholds():
    decision = evaluate_delivery(8.6, threshold=7.0, important_threshold=8.5)
    assert decision.should_send is True
    assert decision.important is True


def test_build_delivery_preview_contains_action_text():
    preview = build_delivery_preview(build_issue(7.8), threshold=7.0, important_threshold=8.5)
    assert preview.decision.should_send is True
    assert '[중요도 7.8 | 일반]' in preview.telegram.body
    assert 'schema 비교' in preview.telegram.body
