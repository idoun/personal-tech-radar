import json
import re
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from markdown_it import MarkdownIt
from sqlalchemy.orm import Session

from app.core.article_keys import build_article_key
from app.core.auth import require_authenticated_user
from app.core.config import settings
from app.core.delivery import build_delivery_log_result, build_delivery_preview
from app.core.profile import load_tech_radar_profile
from app.core.scoring import ArticleScoreResult, build_fallback_score
from app.core.summary import StructuredSummary, build_fallback_structured_summary, parse_structured_summary
from app.db.session import get_db
from app.models.article_favorite import ArticleFavorite
from app.models.issue import Issue
from app.schemas.issue import (
    ArticleFavoriteDeleteRequest,
    ArticleFavoriteDeleteResponse,
    ArticleFavoriteItem,
    ArticleFavoriteUpsertRequest,
    DeliveryLogPayload,
    DeliveryPreviewPayload,
    IssueDeliveryLogRequest,
    IssueDetail,
    IssueGroupMonth,
    IssueIngestRequest,
    IssueIngestResponse,
    IssueListItem,
    IssueScore,
    IssueSearchResponse,
    IssueSearchResult,
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


def _community_reaction_bullets(issue: Issue) -> list[str]:
    return [item.strip() for item in json.loads(issue.community_reaction_bullets_json or '[]') if str(item).strip()]



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
        community_reaction_summary=(issue.community_reaction_summary or '').strip(),
        community_reaction_bullets=_community_reaction_bullets(issue),
    )
    preview = build_delivery_preview(
        detail,
        threshold=settings.tech_radar_min_telegram_score,
        important_threshold=settings.tech_radar_important_score,
    )
    detail.delivery_preview = DeliveryPreviewPayload.model_validate(preview.model_dump())
    return detail


def _favorite_item(record: ArticleFavorite) -> ArticleFavoriteItem:
    return ArticleFavoriteItem.model_validate(record)


def _normalize_search_terms(query: str) -> list[str]:
    tokens = [token.strip().lower() for token in query.split() if token.strip()]
    terms: list[str] = []
    for token in tokens:
        if token not in terms:
            terms.append(token)
    return terms


def _plain_markdown_text(markdown: str) -> str:
    text = markdown
    text = re.sub(r'```[\s\S]*?```', ' ', text)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    text = re.sub(r'!\[[^\]]*\]\([^)]+\)', ' ', text)
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    text = re.sub(r'[#>*_~-]+', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def _build_search_snippet(text: str, matched_terms: list[str], max_length: int = 150) -> str:
    compact = re.sub(r'\s+', ' ', text).strip()
    if not compact:
        return ''

    lowered = compact.lower()
    first_pos = min((lowered.find(term) for term in matched_terms if term in lowered), default=-1)
    if first_pos < 0:
        return compact[:max_length].strip()

    start = max(0, first_pos - max_length // 3)
    end = min(len(compact), start + max_length)
    snippet = compact[start:end].strip()
    if start > 0:
        snippet = f'...{snippet}'
    if end < len(compact):
        snippet = f'{snippet}...'
    return snippet


def _search_issue(issue: Issue, query: str) -> IssueSearchResult | None:
    terms = _normalize_search_terms(query)
    if not terms:
        return None

    structured = _issue_summary(issue)
    score = _issue_score(issue, structured)
    markdown = _read_markdown(issue.markdown_path)
    markdown_text = _plain_markdown_text(markdown)
    searchable_fields = [
        ('title', issue.title, 120),
        ('short_summary', structured.short_summary, 90),
        ('impact_summary', structured.impact_summary, 82),
        ('tags', ' '.join(structured.tags), 78),
        ('summary', issue.summary, 74),
        ('recommended_action', score.recommended_action, 68),
        ('markdown', markdown_text, 52),
    ]

    best_match: tuple[str, str, list[str], float] | None = None
    all_matched_terms: list[str] = []
    normalized_query = ' '.join(terms)

    for field_name, raw_text, weight in searchable_fields:
        text = re.sub(r'\s+', ' ', (raw_text or '')).strip()
        if not text:
            continue

        lowered = text.lower()
        field_matches = [term for term in terms if term in lowered]
        if not field_matches:
            continue

        for term in field_matches:
            if term not in all_matched_terms:
                all_matched_terms.append(term)

        first_pos = min(lowered.find(term) for term in field_matches)
        field_score = float(weight + len(field_matches) * 14)
        if len(field_matches) == len(terms):
            field_score += 18
        if normalized_query and normalized_query in lowered:
            field_score += 16
        field_score -= min(first_pos, 240) / 120.0

        if best_match is None or field_score > best_match[3]:
            best_match = (field_name, text, field_matches, field_score)

    if best_match is None:
        return None

    matched_field, matched_text, matched_terms, match_score = best_match
    recency_bonus = issue.issue_date.toordinal() / 100000.0
    item = IssueListItem(
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
    return IssueSearchResult(
        **item.model_dump(),
        matched_field=matched_field,
        snippet=_build_search_snippet(matched_text, matched_terms),
        matched_terms=all_matched_terms,
        match_score=round(match_score + recency_bonus, 3),
    )


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


@router.get('/article-favorites', response_model=list[ArticleFavoriteItem])
def list_article_favorites(_user_id: int = Depends(require_authenticated_user), db: Session = Depends(get_db)):
    favorites = (
        db.query(ArticleFavorite)
        .filter(ArticleFavorite.user_id == _user_id)
        .order_by(ArticleFavorite.created_at.desc(), ArticleFavorite.id.desc())
        .all()
    )
    return [_favorite_item(record) for record in favorites]


@router.post('/article-favorites', response_model=ArticleFavoriteItem)
def create_article_favorite(
    payload: ArticleFavoriteUpsertRequest,
    _user_id: int = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
):
    article_key = build_article_key(payload.issue_slug, payload.article_title, payload.article_index)
    favorite = (
        db.query(ArticleFavorite)
        .filter(
            ArticleFavorite.user_id == _user_id,
            ArticleFavorite.issue_slug == payload.issue_slug,
            ArticleFavorite.article_key == article_key,
        )
        .first()
    )

    if favorite is None:
        favorite = ArticleFavorite(
            user_id=_user_id,
            issue_slug=payload.issue_slug,
            issue_date=payload.issue_date,
            article_key=article_key,
            article_title=payload.article_title,
            article_index=payload.article_index,
        )
        db.add(favorite)
    else:
        favorite.issue_date = payload.issue_date
        favorite.article_title = payload.article_title
        favorite.article_index = payload.article_index

    db.commit()
    db.refresh(favorite)
    return _favorite_item(favorite)


@router.delete('/article-favorites', response_model=ArticleFavoriteDeleteResponse)
def delete_article_favorite(
    payload: ArticleFavoriteDeleteRequest,
    _user_id: int = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
):
    article_key = build_article_key(payload.issue_slug, payload.article_title, payload.article_index)
    favorite = (
        db.query(ArticleFavorite)
        .filter(
            ArticleFavorite.user_id == _user_id,
            ArticleFavorite.issue_slug == payload.issue_slug,
            ArticleFavorite.article_key == article_key,
        )
        .first()
    )
    if favorite is not None:
        db.delete(favorite)
        db.commit()
    return ArticleFavoriteDeleteResponse()


@router.get('', response_model=list[IssueGroupMonth])
def list_issues(_user_id: int = Depends(require_authenticated_user), db: Session = Depends(get_db)):
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


@router.get('/search', response_model=IssueSearchResponse)
def search_issues(
    q: str = Query(min_length=1, max_length=120),
    _user_id: int = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
):
    query = ' '.join(q.split()).strip()
    if not query:
        return IssueSearchResponse(query='', total=0, items=[])

    issues = (
        db.query(Issue)
        .filter(Issue.is_published.is_(True))
        .order_by(Issue.issue_date.desc(), Issue.id.desc())
        .all()
    )

    results: list[IssueSearchResult] = []
    for issue in issues:
        match = _search_issue(issue, query)
        if match is not None:
            results.append(match)

    results.sort(key=lambda item: (item.match_score, item.issue_date), reverse=True)
    return IssueSearchResponse(query=query, total=len(results), items=results[:50])


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
    community_reaction_summary = (payload.community_reaction_summary or '').strip()
    community_reaction_bullets = [item.strip() for item in payload.community_reaction_bullets if item.strip()][:2]

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
    issue.community_reaction_summary = community_reaction_summary[:160]
    issue.community_reaction_bullets_json = json.dumps(community_reaction_bullets, ensure_ascii=False)
    issue.issue_date = payload.issue_date
    issue.year = payload.issue_date.year
    issue.month = payload.issue_date.month
    issue.markdown_path = markdown_path
    issue.is_published = payload.is_published
    db.commit()
    db.refresh(issue)

    return IssueIngestResponse(slug=slug, markdown_path=markdown_path, created=created, issue=_issue_detail(issue))


@router.get('/latest', response_model=IssueDetail)
def latest_issue(_user_id: int = Depends(require_authenticated_user), db: Session = Depends(get_db)):
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
def get_issue(slug: str, _user_id: int = Depends(require_authenticated_user), db: Session = Depends(get_db)):
    issue = db.query(Issue).filter(Issue.slug == slug, Issue.is_published.is_(True)).first()
    if not issue:
        raise HTTPException(status_code=404, detail='Issue not found')
    try:
        return _issue_detail(issue)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail='Issue content missing')


@router.get('/{slug}/delivery-preview', response_model=DeliveryPreviewPayload)
def get_issue_delivery_preview(
    slug: str,
    _user_id: int = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
):
    issue = db.query(Issue).filter(Issue.slug == slug, Issue.is_published.is_(True)).first()
    if not issue:
        raise HTTPException(status_code=404, detail='Issue not found')
    detail = _issue_detail(issue)
    if not detail.delivery_preview:
        raise HTTPException(status_code=500, detail='Delivery preview unavailable')
    return detail.delivery_preview


@router.post('/{slug}/delivery-log', response_model=DeliveryLogPayload)
def record_issue_delivery_log(
    slug: str,
    payload: IssueDeliveryLogRequest,
    _user_id: int = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
):
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
