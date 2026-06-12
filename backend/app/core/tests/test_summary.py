from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from app.core.summary import build_fallback_structured_summary, parse_structured_summary


def test_parse_structured_summary_from_valid_json():
    summary = parse_structured_summary(
        '{"short_summary":"짧은 요약","impact_summary":"영향 설명","action_items":["a","b"],"tags":["AI","Agent"],"radar_category":"AI Agent","radar_status":"Trial"}'
    )

    assert summary.short_summary == '짧은 요약'
    assert summary.impact_summary == '영향 설명'
    assert summary.action_items == ['a', 'b']
    assert summary.tags == ['AI', 'Agent']
    assert summary.radar_category == 'AI Agent'
    assert summary.radar_status == 'Trial'


def test_parse_structured_summary_falls_back_for_plain_text():
    summary = parse_structured_summary('기존 단일 요약 문자열')

    assert summary.short_summary == '기존 단일 요약 문자열'
    assert summary.impact_summary
    assert summary.action_items
    assert summary.tags == ['GeekNews']
    assert summary.radar_category == 'Other'
    assert summary.radar_status == 'Assess'


def test_parse_structured_summary_uses_markdown_body_for_fallback_quality():
    markdown = '''
# GeekNews

## Agent observability toolkit
- 요약: Agent tracing과 replay 흐름을 다룬다.
- 원문: https://github.com/example/agent-observability
'''
    summary = parse_structured_summary('에이전트 관찰성 도구 소개', markdown=markdown)

    assert summary.radar_category == 'AI Agent'
    assert summary.radar_status == 'Trial'
    assert any('README' in item or '저장소' in item for item in summary.action_items)
    assert 'Agent observability toolkit' in summary.impact_summary
    assert '현재 진행 중인 프로젝트' in summary.impact_summary


def test_build_fallback_structured_summary_uses_representative_titles_in_impact_summary():
    markdown = '''
# GeekNews

## Agent observability toolkit
- 요약: Agent tracing과 replay 흐름을 다룬다.
- 원문: https://github.com/example/agent-observability

## Terminal utility update
- 요약: CLI와 터미널 생산성 향상 도구를 소개한다.
- 원문: https://example.com/cli-tool
'''
    summary = build_fallback_structured_summary('에이전트 관찰성 도구 소개', markdown=markdown)

    assert 'Agent observability toolkit와 Terminal utility update' in summary.impact_summary
    assert '같은 주제를 통해' in summary.impact_summary



def test_build_fallback_structured_summary_uses_korean_particle_for_titles():
    markdown = '''
# GeekNews

## 에이전트 엔진
- 요약: Agent orchestration 흐름을 다룬다.
- 원문: https://github.com/example/agent-engine

## 터미널 도구
- 요약: CLI 생산성 향상 도구를 소개한다.
- 원문: https://example.com/cli-tool
'''
    summary = build_fallback_structured_summary('개발 도구 중심 이슈', markdown=markdown)

    assert '에이전트 엔진과 터미널 도구' in summary.impact_summary


def test_parse_structured_summary_avoids_overeager_ai_category():
    markdown = '''
# GeekNews

## Terminal utility update
- 요약: CLI와 터미널 생산성 향상 도구를 소개한다.
- 원문: https://example.com/cli-tool

## Small AI note
- 요약: AI 관련 짧은 언급이 있다.
- 원문: https://example.com/ai-note
'''
    summary = parse_structured_summary('개발 도구 중심 이슈', markdown=markdown)

    assert summary.radar_category == 'DevTools'


def test_build_fallback_structured_summary_uses_safe_defaults():
    summary = build_fallback_structured_summary('')

    assert summary.short_summary == 'GeekNews 요약 아카이브'
    assert summary.impact_summary
    assert summary.action_items
