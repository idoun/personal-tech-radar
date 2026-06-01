from fastapi import APIRouter, Depends, HTTPException
from markdown_it import MarkdownIt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.issue import Issue
from app.schemas.issue import IssueDetail, IssueGroupMonth, IssueIngestRequest, IssueIngestResponse, IssueListItem

router = APIRouter(prefix='/api/issues', tags=['issues'])
md = MarkdownIt('commonmark', {'html': False, 'linkify': True, 'typographer': True}).enable('table')


def _read_markdown(markdown_path: str) -> str:
    path = (settings.content_root_path / markdown_path).resolve()
    if not path.exists() or settings.content_root_path not in path.parents:
        raise FileNotFoundError(markdown_path)
    return path.read_text(encoding='utf-8')


def _issue_detail(issue: Issue) -> IssueDetail:
    markdown = _read_markdown(issue.markdown_path)
    return IssueDetail(
        **IssueListItem.model_validate(issue).model_dump(),
        markdown=markdown,
        html=md.render(markdown),
        markdown_path=issue.markdown_path,
    )


def _make_slug(payload: IssueIngestRequest) -> str:
    return payload.slug or payload.issue_date.isoformat()


def _write_markdown(issue_date, slug: str, markdown: str) -> str:
    rel_path = f'{issue_date.year:04d}/{issue_date.month:02d}/{slug}-geeknews.md'
    path = (settings.content_root_path / rel_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown.strip() + '\n', encoding='utf-8')
    return rel_path


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
        grouped.setdefault(key, []).append(IssueListItem.model_validate(issue))

    result: list[IssueGroupMonth] = []
    for (year, month), items in grouped.items():
        result.append(IssueGroupMonth(year=year, month=month, label=f'{year}-{month:02d}', items=items))
    return result


@router.post('/ingest', response_model=IssueIngestResponse)
def ingest_issue(payload: IssueIngestRequest, db: Session = Depends(get_db)):
    slug = _make_slug(payload)
    markdown_path = _write_markdown(payload.issue_date, slug, payload.markdown)
    issue = db.query(Issue).filter(Issue.slug == slug).first()
    created = issue is None
    if issue is None:
        issue = Issue(slug=slug)
        db.add(issue)

    issue.title = payload.title
    issue.summary = payload.summary
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
