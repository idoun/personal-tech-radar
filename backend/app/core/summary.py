from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from app.core.issue_analysis import parse_issue_markdown


RADAR_CATEGORIES = {
    'AI Agent',
    'LLM Serving',
    'RAG / Memory',
    'DevTools',
    'Infra / Cloud',
    'Security',
    'Product / UX',
    'Open Source',
    'Other',
}

RADAR_STATUSES = {'Adopt', 'Trial', 'Assess', 'Hold'}


class StructuredSummary(BaseModel):
    short_summary: str
    impact_summary: str
    action_items: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    radar_category: str = 'Other'
    radar_status: str = 'Assess'


FALLBACK_SHORT_SUMMARY = 'GeekNews 요약 아카이브'
FALLBACK_IMPACT_SUMMARY = '이번 요약은 핵심 주제를 빠르게 훑고, 현재 프로젝트와 연결 가능한 실험 포인트를 찾는 용도로 볼 수 있습니다.'
FALLBACK_ACTION_ITEMS = ['원문과 요약 내용을 검토해 후속 액션을 수동으로 정리한다.']
FALLBACK_TAGS = ['GeekNews']



def _topic_connector(text: str) -> str:
    stripped = (text or '').rstrip()
    if not stripped:
        return '와'
    code = ord(stripped[-1])
    if 0xAC00 <= code <= 0xD7A3:
        return '과' if (code - 0xAC00) % 28 else '와'
    return '와'



def _normalize_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    return [str(value).strip()] if str(value).strip() else []



def build_fallback_structured_summary(summary: str, markdown: str | None = None) -> StructuredSummary:
    normalized = summary.strip() or FALLBACK_SHORT_SUMMARY
    analysis = parse_issue_markdown(markdown or '') if markdown else None

    tags = FALLBACK_TAGS.copy()
    radar_category = 'Other'
    radar_status = 'Assess'
    impact_summary = FALLBACK_IMPACT_SUMMARY
    action_items = FALLBACK_ACTION_ITEMS.copy()

    if analysis and analysis.cards:
        dominant_category, category_score = analysis.dominant_category()
        if category_score >= 1:
            radar_category = dominant_category
            tags = ['GeekNews', dominant_category]

        category_keywords = {
            'AI Agent': ['agent', 'ai', 'llm', 'qwen', 'langgraph', 'mcp'],
            'LLM Serving': ['vllm', 'sglang', 'inference', 'serving', 'gpu'],
            'Security': ['security', 'sandbox', 'auth', 'ssh'],
            'DevTools': ['cli', 'terminal', 'devtools', 'editor', 'debug', 'tool'],
            'Infra / Cloud': ['cloud', 'server', 'infra', 'kubernetes', 'database'],
        }
        representative = analysis.best_matching_card(category_keywords.get(radar_category, [])) or analysis.cards[0]
        representative_title = representative.title.strip() if representative.title else '핵심 카드'
        second_title = analysis.cards[1].title.strip() if len(analysis.cards) > 1 and analysis.cards[1].title.strip() else None

        if second_title:
            connector = _topic_connector(representative_title)
            impact_summary = (
                f"이번 이슈는 {representative_title}{connector} {second_title} 같은 주제를 통해, "
                '현재 진행 중인 프로젝트에 참고할 도구와 구현 흐름을 빠르게 훑는 데 의미가 있습니다.'
            )
        else:
            impact_summary = (
                f"이번 이슈는 {representative_title} 같은 주제를 중심으로, "
                '현재 진행 중인 프로젝트에 참고할 도구와 구현 흐름을 빠르게 훑는 데 의미가 있습니다.'
            )

        if (representative.source or '').startswith('https://github.com/'):
            radar_status = 'Trial'
            action_items = [
                f"{representative_title} 저장소의 README와 예제 구조를 검토한다.",
                '현재 프로젝트와 바로 비교할 수 있는 포인트를 1~2개 정리한다.',
            ]
        else:
            action_items = [
                f"{representative_title} 관련 원문 링크를 먼저 검토한다.",
                '현재 프로젝트에 적용 가능한 아이디어가 있는지 체크한다.',
            ]

    return StructuredSummary(
        short_summary=normalized,
        impact_summary=impact_summary,
        action_items=action_items,
        tags=tags,
        radar_category=radar_category,
        radar_status=radar_status,
    )



def parse_structured_summary(summary: str, *, fallback_summary: str | None = None, markdown: str | None = None) -> StructuredSummary:
    text = summary.strip()
    fallback_seed = fallback_summary if fallback_summary is not None else summary

    if not text:
        return build_fallback_structured_summary(fallback_seed, markdown=markdown)

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return build_fallback_structured_summary(fallback_seed, markdown=markdown)

    if not isinstance(data, dict):
        return build_fallback_structured_summary(fallback_seed, markdown=markdown)

    normalized = {
        'short_summary': str(data.get('short_summary', '')).strip(),
        'impact_summary': str(data.get('impact_summary', '')).strip(),
        'action_items': _normalize_list(data.get('action_items')),
        'tags': _normalize_list(data.get('tags')),
        'radar_category': str(data.get('radar_category', 'Other')).strip() or 'Other',
        'radar_status': str(data.get('radar_status', 'Assess')).strip() or 'Assess',
    }

    if normalized['radar_category'] not in RADAR_CATEGORIES:
        normalized['radar_category'] = 'Other'
    if normalized['radar_status'] not in RADAR_STATUSES:
        normalized['radar_status'] = 'Assess'

    if not normalized['short_summary']:
        normalized['short_summary'] = (fallback_summary or FALLBACK_SHORT_SUMMARY).strip() or FALLBACK_SHORT_SUMMARY
    if not normalized['impact_summary']:
        normalized['impact_summary'] = build_fallback_structured_summary(fallback_seed, markdown=markdown).impact_summary
    if not normalized['action_items']:
        normalized['action_items'] = build_fallback_structured_summary(fallback_seed, markdown=markdown).action_items
    if not normalized['tags']:
        normalized['tags'] = build_fallback_structured_summary(fallback_seed, markdown=markdown).tags

    try:
        return StructuredSummary.model_validate(normalized)
    except ValidationError:
        return build_fallback_structured_summary(fallback_seed, markdown=markdown)



def encode_structured_summary(summary: StructuredSummary) -> str:
    return json.dumps(summary.model_dump(), ensure_ascii=False)
