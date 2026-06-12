import json
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException
from markdown_it import MarkdownIt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.delivery import build_delivery_log_result, build_delivery_preview
from app.core.profile import load_tech_radar_profile
from app.core.scoring import ArticleScoreResult, build_fallback_score
from app.core.summary import StructuredSummary, build_fallback_structured_summary, parse_structured_summary
from app.db.session import get_db
from app.models.issue import Issue
from app.schemas.issue import (
    DeliveryLogPayload,
    DeliveryPreviewPayload,
    IssueDeliveryLogRequest,
    IssueDetail,
    IssueGroupMonth,
    IssueIngestRequest,
    IssueIngestResponse,
    IssueListItem,
    IssueScore,
)

router = APIRouter(prefix='/api/issues', tags=['issues'])
md = MarkdownIt('commonmark', {'html': False, 'linkify': True, 'typographer': True}).enable('table')


def _read_markdown(markdown_path: str) -> str:
    path = (settings.content_root_path / markdown_path).resolve()
    if not path.exists() or settings.content_root_path not in path.parents:
        raise FileNotFoundError(markdown_path)
    return path.read_text(encoding='utf-8')


def _issue_summary(issue: Issue) -> StructuredSummary:
    if issue.short_summary and issue.impact_summary:
        return StructuredSummary(
            short_summary=issue.short_summary,
            impact_summary=issue.impact_summary,
            action_items=json.loads(issue.action_items_json or '[]'),
            tags=json.loads(issue.tags_json or '[]'),
            radar_category=issue.radar_category or 'Other',
            radar_status=issue.radar_status or 'Assess',
        )
    return parse_structured_summary(issue.summary, fallback_summary=issue.summary, markdown=_read_markdown(issue.markdown_path))



def _issue_score(issue: Issue, structured: StructuredSummary | None = None) -> ArticleScoreResult:
    structured = structured or _issue_summary(issue)
    if issue.final_score > 0 or issue.score_reason or issue.recommended_action:
        return ArticleScoreResult(
            interest_score=issue.interest_score,
            project_score=issue.project_score,
            novelty_score=issue.novelty_score,
            actionability_score=issue.actionability_score,
            credibility_score=issue.credibility_score,
            community_score=issue.community_score,
            final_score=issue.final_score,
            reason=issue.score_reason or '저장된 점수 설명이 없습니다.',
            recommended_action=issue.recommended_action or (structured.action_items[0] if structured.action_items else ''),
        )
    return build_fallback_score(issue.title, structured, load_tech_radar_profile(), markdown=_read_markdown(issue.markdown_path))



def _issue_list_item(issue: Issue) -> IssueListItem:
    structured = _issue_summary(issue)
    score = _issue_score(issue, structured)
    return IssueListItem(
        id=issue.id,
        slug=issue.slug,
        title=issue.title,
        summary=issue.summary,
        short_summary=structured.short_summary,
        impact_summary=structured.impact_summary,
        action_items=structured.action_items,
        tags=structured.tags,
        radar_category=structured.radar_category,
        radar_status=structured.radar_status,
        score=IssueScore.model_validate(score.model_dump()),
        issue_date=issue.issue_date,
        year=issue.year,
        month=issue.month,
        is_published=issue.is_published,
    )



def _issue_detail(issue: Issue) -> IssueDetail:
    markdown = _read_markdown(issue.markdown_path)
    detail = IssueDetail(
        **_issue_list_item(issue).model_dump(),
        markdown=markdown,
        html=md.render(markdown),
        markdown_path=issue.markdown_path,
    )
    preview = build_delivery_preview(
        detail,
        threshold=settings.tech_radar_min_telegram_score,
        important_threshold=settings.tech_radar_important_score,
    )
    detail.delivery_preview = DeliveryPreviewPayload.model_validate(preview.model_dump())
    return detail


def _make_slug(payload: IssueIngestRequest) -> str:
    return payload.slug or payload.issue_date.isoformat()


def _write_markdown(issue_date, slug: str, markdown: str) -> str:
    rel_path = f'{issue_date.year:04d}/{issue_date.month:02d}/{slug}-geeknews.md'
    path = (settings.content_root_path / rel_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown.strip() + '\n', encoding='utf-8')
    return rel_path


def _require_ingest_token(x_ingest_token: str | None = Header(default=None)):
    if not settings.ingest_token:
        raise HTTPException(status_code=503, detail='Ingest token is not configured')
    if x_ingest_token != settings.ingest_token:
        raise HTTPException(status_code=401, detail='Invalid ingest token')


@router.get('', response_model=list[IssueGroupMonth])
def list_issues(db: Session = Depends(get_db)):
    issues = (
        db.query(Issue)
        .filter(Issue.is_published.is_(True))
        .order_by(Issue.issue_date.desc(), Issue.id.desc())
        .all()
    )

    grouped: dict[tuple[int, int], list[IssueListItem]] = {}
    for issue in issues:
        key = (issue.year, issue.month)
        grouped.setdefault(key, []).append(_issue_list_item(issue))

    result: list[IssueGroupMonth] = []
    for (year, month), items in grouped.items():
        result.append(IssueGroupMonth(year=year, month=month, label=f'{year}-{month:02d}', items=items))
    return result


@router.post('/ingest', response_model=IssueIngestResponse, dependencies=[Depends(_require_ingest_token)])
def ingest_issue(payload: IssueIngestRequest, db: Session = Depends(get_db)):
    slug = _make_slug(payload)
    markdown_path = _write_markdown(payload.issue_date, slug, payload.markdown)
    issue = db.query(Issue).filter(Issue.slug == slug).first()
    created = issue is None
    if issue is None:
        issue = Issue(slug=slug)
        db.add(issue)

    structured = build_fallback_structured_summary(payload.summary, markdown=payload.markdown)
    if payload.short_summary:
        structured.short_summary = payload.short_summary.strip() or structured.short_summary
    if payload.impact_summary:
        structured.impact_summary = payload.impact_summary.strip() or structured.impact_summary
    if payload.action_items:
        structured.action_items = [item.strip() for item in payload.action_items if item.strip()] or structured.action_items
    if payload.tags:
        structured.tags = [tag.strip() for tag in payload.tags if tag.strip()] or structured.tags
    if payload.radar_category:
        structured.radar_category = payload.radar_category.strip() or structured.radar_category
    if payload.radar_status:
        structured.radar_status = payload.radar_status.strip() or structured.radar_status

    score = build_fallback_score(payload.title, structured, load_tech_radar_profile(), markdown=payload.markdown)
    if payload.interest_score is not None:
        score.interest_score = payload.interest_score
    if payload.project_score is not None:
        score.project_score = payload.project_score
    if payload.novelty_score is not None:
        score.novelty_score = payload.novelty_score
    if payload.actionability_score is not None:
        score.actionability_score = payload.actionability_score
    if payload.credibility_score is not None:
        score.credibility_score = payload.credibility_score
    if payload.community_score is not None:
        score.community_score = payload.community_score
    if payload.final_score is not None:
        score.final_score = payload.final_score
    if payload.score_reason:
        score.reason = payload.score_reason.strip() or score.reason
    if payload.recommended_action:
        score.recommended_action = payload.recommended_action.strip() or score.recommended_action

    issue.title = payload.title
    issue.summary = payload.summary
    issue.short_summary = structured.short_summary
    issue.impact_summary = structured.impact_summary
    issue.action_items_json = json.dumps(structured.action_items, ensure_ascii=False)
    issue.tags_json = json.dumps(structured.tags, ensure_ascii=False)
    issue.radar_category = structured.radar_category
    issue.radar_status = structured.radar_status
    issue.interest_score = score.interest_score
    issue.project_score = score.project_score
    issue.novelty_score = score.novelty_score
    issue.actionability_score = score.actionability_score
    issue.credibility_score = score.credibility_score
    issue.community_score = score.community_score
    issue.final_score = score.final_score
    issue.score_reason = score.reason
    issue.recommended_action = score.recommended_action
    issue.issue_date = payload.issue_date
    issue.year = payload.issue_date.year
    issue.month = payload.issue_date.month
    issue.markdown_path = markdown_path
    issue.is_published = payload.is_published
    db.commit()
    db.refresh(issue)

    return IssueIngestResponse(slug=slug, markdown_path=markdown_path, created=created, issue=_issue_detail(issue))


@router.get('/latest', response_model=IssueDetail)
def latest_issue(db: Session = Depends(get_db)):
    issue = (
        db.query(Issue)
        .filter(Issue.is_published.is_(True))
        .order_by(Issue.issue_date.desc(), Issue.id.desc())
        .first()
    )
    if not issue:
        raise HTTPException(status_code=404, detail='No issue found')
    return _issue_detail(issue)


@router.get('/{slug}', response_model=IssueDetail)
def get_issue(slug: str, db: Session = Depends(get_db)):
    issue = db.query(Issue).filter(Issue.slug == slug, Issue.is_published.is_(True)).first()
    if not issue:
        raise HTTPException(status_code=404, detail='Issue not found')
    try:
        return _issue_detail(issue)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail='Issue content missing')


@router.get('/{slug}/delivery-preview', response_model=DeliveryPreviewPayload)
def get_issue_delivery_preview(slug: str, db: Session = Depends(get_db)):
    issue = db.query(Issue).filter(Issue.slug == slug, Issue.is_published.is_(True)).first()
    if not issue:
        raise HTTPException(status_code=404, detail='Issue not found')
    detail = _issue_detail(issue)
    if not detail.delivery_preview:
        raise HTTPException(status_code=500, detail='Delivery preview unavailable')
    return detail.delivery_preview


@router.post('/{slug}/delivery-log', response_model=DeliveryLogPayload)
def record_issue_delivery_log(slug: str, payload: IssueDeliveryLogRequest, db: Session = Depends(get_db)):
    issue = db.query(Issue).filter(Issue.slug == slug).first()
    if not issue:
        raise HTTPException(status_code=404, detail='Issue not found')

    sent_at = datetime.fromisoformat(payload.sent_at) if payload.sent_at else datetime.utcnow()
    if payload.channel == 'telegram':
        issue.telegram_sent = payload.status == 'sent'
        issue.telegram_sent_at = sent_at if payload.status == 'sent' else None
        issue.telegram_message = payload.message
        issue.telegram_error = payload.error or ''
        db.commit()

    return DeliveryLogPayload.model_validate(
        build_delivery_log_result(
            article_slug=issue.slug,
            channel=payload.channel,
            status=payload.status,
            message=payload.message,
            error=payload.error,
            sent_at=sent_at,
        ).model_dump()
    )
