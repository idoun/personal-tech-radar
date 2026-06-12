from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel

from app.schemas.issue import IssueDetail


class DeliveryDecision(BaseModel):
    should_send: bool
    important: bool
    threshold: float
    important_threshold: float
    reason: str


class TelegramPreview(BaseModel):
    title: str
    body: str


class DeliveryPreview(BaseModel):
    article_slug: str
    channel: str
    decision: DeliveryDecision
    telegram: TelegramPreview


class DeliveryLogResult(BaseModel):
    id: str
    article_slug: str
    channel: str
    status: str
    message: str
    sent_at: str | None
    error: str | None


def evaluate_delivery(score: float, *, threshold: float, important_threshold: float) -> DeliveryDecision:
    should_send = score >= threshold
    important = score >= important_threshold
    if should_send:
        reason = f'final_score {score:.2f}가 전송 기준 {threshold:.2f} 이상입니다.'
    else:
        reason = f'final_score {score:.2f}가 전송 기준 {threshold:.2f} 미만입니다.'
    return DeliveryDecision(
        should_send=should_send,
        important=important,
        threshold=threshold,
        important_threshold=important_threshold,
        reason=reason,
    )


def format_telegram_message(issue: IssueDetail, decision: DeliveryDecision) -> TelegramPreview:
    importance_label = '중요' if decision.important else '일반'
    score = issue.score.final_score
    project_hint = issue.score.reason
    action_lines = '\n'.join(f'{idx}. {item}' for idx, item in enumerate(issue.action_items, start=1)) or '1. 후속 액션 없음'
    tags = ', '.join(issue.tags) if issue.tags else '태그 없음'

    body = (
        f'[중요도 {score:.1f} | {importance_label}] {issue.title}\n\n'
        f'10초 요약:\n{issue.short_summary}\n\n'
        f'왜 중요한가:\n{issue.impact_summary}\n\n'
        f'내 프로젝트 연결:\n{project_hint}\n\n'
        f'Action:\n{action_lines}\n\n'
        f'Radar: {issue.radar_category} / {issue.radar_status}\n'
        f'태그: {tags}\n'
        f'원문 아카이브: /technews/{issue.slug}'
    )
    return TelegramPreview(title=issue.title, body=body)


def build_delivery_preview(issue: IssueDetail, *, threshold: float, important_threshold: float) -> DeliveryPreview:
    decision = evaluate_delivery(issue.score.final_score, threshold=threshold, important_threshold=important_threshold)
    telegram = format_telegram_message(issue, decision)
    return DeliveryPreview(article_slug=issue.slug, channel='telegram', decision=decision, telegram=telegram)


def build_delivery_log_result(article_slug: str, channel: str, status: str, message: str, *, error: str | None = None, sent_at: datetime | None = None) -> DeliveryLogResult:
    return DeliveryLogResult(
        id=str(uuid4()),
        article_slug=article_slug,
        channel=channel,
        status=status,
        message=message,
        sent_at=sent_at.isoformat() if sent_at else None,
        error=error,
    )
