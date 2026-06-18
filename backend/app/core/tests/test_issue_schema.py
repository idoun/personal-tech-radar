from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from app.schemas.issue import IssueDetail, IssueScore


def test_issue_detail_supports_optional_community_reaction_fields():
    detail = IssueDetail(
        id=1,
        slug='2026-06-18',
        title='Community reaction sample',
        summary='legacy summary',
        short_summary='짧은 요약',
        impact_summary='영향 요약',
        action_items=['follow up'],
        tags=['GeekNews'],
        radar_category='AI Systems',
        radar_status='Assess',
        score=IssueScore(
            interest_score=7.0,
            project_score=7.0,
            novelty_score=6.5,
            actionability_score=7.0,
            credibility_score=6.0,
            community_score=5.5,
            final_score=6.7,
            reason='sample reason',
            recommended_action='read the source',
        ),
        issue_date='2026-06-18',
        year=2026,
        month=6,
        is_published=True,
        markdown='body',
        html='<p>body</p>',
        markdown_path='2026/06/sample.md',
        community_reaction_summary='댓글에서는 비용 대비 효과를 더 궁금해했다.',
        community_reaction_bullets=['벤치마크보다 운영 안정성이 더 중요하다는 반응이 있었다.'],
    )

    assert detail.community_reaction_summary
    assert len(detail.community_reaction_bullets) == 1
