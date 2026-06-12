from __future__ import annotations

import math
import re

from pydantic import BaseModel

from app.core.issue_analysis import parse_issue_markdown
from app.core.profile import TechRadarProfile
from app.core.summary import StructuredSummary


class ArticleScoreResult(BaseModel):
    interest_score: float
    project_score: float
    novelty_score: float
    actionability_score: float
    credibility_score: float
    community_score: float
    final_score: float
    reason: str
    recommended_action: str


WEIGHTS = {
    'interest_score': 0.30,
    'project_score': 0.25,
    'novelty_score': 0.15,
    'actionability_score': 0.15,
    'credibility_score': 0.10,
    'community_score': 0.05,
}


def _clamp(value: float) -> float:
    return round(max(0.0, min(10.0, value)), 2)


def _contains_any(text: str, keywords: list[str]) -> int:
    lowered = text.lower()
    return sum(1 for keyword in keywords if keyword.lower() in lowered)


def _normalize_text(text: str) -> str:
    return re.sub(r'\s+', ' ', text.lower()).strip()


def _keyword_hit_strength(text: str, keyword: str) -> float:
    normalized_text = _normalize_text(text)
    normalized_keyword = _normalize_text(keyword)
    if not normalized_keyword:
        return 0.0
    if normalized_keyword in normalized_text:
        return 1.0

    tokens = [token for token in re.split(r'[^a-z0-9+#.-]+', normalized_keyword) if token]
    if not tokens:
        return 0.0

    present_tokens = sum(1 for token in tokens if token in normalized_text)
    if present_tokens == len(tokens):
        return 0.75
    if len(tokens) >= 2 and present_tokens >= math.ceil(len(tokens) / 2):
        return 0.4
    return 0.0


def _keyword_match_total(text: str, keywords: list[str]) -> float:
    return round(sum(_keyword_hit_strength(text, keyword) for keyword in keywords), 2)


def compute_final_score(values: dict[str, float]) -> float:
    total = 0.0
    for key, weight in WEIGHTS.items():
        total += values[key] * weight
    return round(total, 2)


def build_fallback_score(title: str, summary: StructuredSummary, profile: TechRadarProfile, markdown: str | None = None) -> ArticleScoreResult:
    analysis = parse_issue_markdown(markdown or '') if markdown else None
    body_text = analysis.combined_text if analysis else ''
    text = ' '.join(
        [
            title,
            summary.short_summary,
            summary.impact_summary,
            ' '.join(summary.action_items),
            ' '.join(summary.tags),
            summary.radar_category,
            summary.radar_status,
            body_text,
        ]
    )

    interest_hits = _keyword_match_total(text, profile.interests)
    interest_score = _clamp(3.8 + min(interest_hits, 6.0) * 0.9)

    project_match_counts = [
        _keyword_match_total(text, project.keywords + [project.name, project.description]) for project in profile.projects
    ]
    ranked_project_hits = sorted(project_match_counts, reverse=True)
    best_project_hits = ranked_project_hits[0] if ranked_project_hits else 0.0
    second_project_hits = ranked_project_hits[1] if len(ranked_project_hits) > 1 else 0.0
    multi_project_bonus = min(sum(1 for hits in project_match_counts if hits >= 1.0) * 0.25, 0.75)
    project_signal = best_project_hits + second_project_hits * 0.35 + multi_project_bonus
    project_score = _clamp(3.6 + min(project_signal, 6.0) * 0.95)

    novelty_seed = len(set(tag.lower() for tag in summary.tags))
    novelty_score = _clamp(4.8 + min(novelty_seed, 4) * 0.7)

    actionability_seed = len(summary.action_items)
    actionability_score = _clamp(4.9 + min(actionability_seed, 3) * 0.95)

    credibility_seed = 5.8
    if 'GeekNews' in summary.tags:
        credibility_seed += 0.5
    if 'Open Source' == summary.radar_category:
        credibility_seed += 0.5
    credibility_score = _clamp(credibility_seed)

    community_seed = 4.6
    if summary.radar_status in {'Adopt', 'Trial'}:
        community_seed += 0.9
    community_score = _clamp(community_seed)

    values = {
        'interest_score': interest_score,
        'project_score': project_score,
        'novelty_score': novelty_score,
        'actionability_score': actionability_score,
        'credibility_score': credibility_score,
        'community_score': community_score,
    }
    final_score = compute_final_score(values)

    top_project_index = project_match_counts.index(best_project_hits) if project_match_counts else None
    top_project_name = profile.projects[top_project_index].name if top_project_index is not None and best_project_hits > 0 else '직접 연결된 프로젝트 없음'

    if analysis and top_project_index is not None and best_project_hits > 0:
        project_keywords = profile.projects[top_project_index].keywords
        representative_card = analysis.best_matching_card(project_keywords)
    else:
        representative_card = None

    if top_project_name != '직접 연결된 프로젝트 없음':
        reason = (
            f"이 이슈는 '{top_project_name}'와 맞닿은 키워드가 포착돼 관련도가 높게 평가됐습니다. "
            f"본문과 요약에서 반복된 기술 키워드, 유사 표현, 그리고 보조 프로젝트와의 겹침까지 반영해 점수화했습니다."
        )
    else:
        reason = (
            '직접적으로 겹치는 프로젝트 키워드는 많지 않았지만, 본문과 요약에 드러난 기술 주제와 '
            '유사 표현까지 함께 보며 관심사 적합도와 실험 가능성을 반영했습니다.'
        )
    if representative_card and representative_card.source:
        recommended_action = f"{representative_card.title} 항목을 먼저 검토하고 현재 프로젝트와 비교 포인트를 정리합니다."
    else:
        recommended_action = summary.action_items[0] if summary.action_items else '원문을 검토해 적용 가능한 액션을 정리합니다.'

    return ArticleScoreResult(final_score=final_score, reason=reason, recommended_action=recommended_action, **values)
