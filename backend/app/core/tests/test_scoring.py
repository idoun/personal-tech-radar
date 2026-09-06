from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from app.core.profile import load_tech_radar_profile
from app.core.scoring import build_fallback_score, compute_final_score
from app.core.summary import StructuredSummary


def test_compute_final_score_uses_weighted_formula():
    score = compute_final_score(
        {
            'interest_score': 8.0,
            'project_score': 6.0,
            'novelty_score': 5.0,
            'actionability_score': 7.0,
            'credibility_score': 6.0,
            'community_score': 4.0,
        }
    )

    assert score == 6.5



def test_build_fallback_score_returns_bounded_values(tmp_path: Path):
    profile_path = tmp_path / 'profile.yaml'
    profile_path.write_text(
        '''
profile:
  interests:
    - AI Systems
    - DevTools
  projects:
    - name: Observability and Replay Toolkit
      description: observability tool
      keywords:
        - tracing
        - replay
'''.strip()
        + '\n',
        encoding='utf-8',
    )

    profile = load_tech_radar_profile(str(profile_path))
    structured = StructuredSummary(
        short_summary='AI systems observability tool overview',
        impact_summary='Directly relevant to tracing and replay workflows.',
        action_items=['event schema 비교'],
        tags=['GeekNews', 'AI Systems', 'DevTools'],
        radar_category='AI Systems',
        radar_status='Trial',
    )

    markdown = '''
# GeekNews

## Agent observability tool
- 요약: tracing 과 replay 구조를 다룸
- 원문: https://github.com/example/agent-observability
'''
    score = build_fallback_score('Agent observability tool', structured, profile, markdown=markdown)

    assert 0 <= score.final_score <= 10
    assert score.interest_score >= 3
    assert score.project_score >= 2.5
    assert score.reason
    assert '프로젝트' in score.reason or '키워드' in score.reason
    assert score.recommended_action == 'event schema 비교'


def test_build_fallback_score_rewards_partial_project_matches(tmp_path: Path):
    profile_path = tmp_path / 'profile.yaml'
    profile_path.write_text(
        '''
profile:
  interests:
    - AI Systems
  projects:
    - name: Observability and Replay Toolkit
      description: agent tracing and replay system
      keywords:
        - agent observability
        - tool call log
        - replay
'''.strip()
        + '\n',
        encoding='utf-8',
    )

    profile = load_tech_radar_profile(str(profile_path))
    structured = StructuredSummary(
        short_summary='Tracing toolkit for agent workflows',
        impact_summary='Useful for observability, tool-call debugging, and replay.',
        action_items=['compare replay flow'],
        tags=['AI Systems'],
        radar_category='AI Systems',
        radar_status='Trial',
    )

    score = build_fallback_score(
        'Open source tracing toolkit',
        structured,
        profile,
        markdown='This project improves observability and tool calling replay for agent systems.',
    )

    assert score.project_score >= 5.5
    assert score.final_score >= 5.5


def test_build_fallback_score_uses_expanded_project_profile_keywords():
    # Keep this fixture independent from a developer's absolute .env profile path.
    profile_path = Path(__file__).resolve().parents[4] / 'config' / 'tech-radar-profile.yaml'
    profile = load_tech_radar_profile(str(profile_path))
    structured = StructuredSummary(
        short_summary='Self-hosted LLM serving stack improves local inference throughput',
        impact_summary='The write-up compares quantization choices, tensor parallel trade-offs, and GPU serving ergonomics.',
        action_items=['compare serving stack'],
        tags=['ML Infrastructure', 'Developer Tools'],
        radar_category='AI Systems',
        radar_status='Trial',
    )

    markdown = '''
# Serving stack notes

## Self-hosted inference engine
- 요약: private LLM deployment with quantization and tensor parallel tuning.
- 원문: https://example.com/self-hosted-llm
'''

    score = build_fallback_score('Self-hosted inference engine', structured, profile, markdown=markdown)

    assert score.project_score >= 7.0
    assert 'Self-hosted Model Serving Stack' in score.reason
