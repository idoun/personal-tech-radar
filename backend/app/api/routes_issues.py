from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from markdown_it import MarkdownIt
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.issue import Issue
from app.schemas.issue import IssueDetail, IssueGroupMonth, IssueListItem
from app.core.config import settings

router = APIRouter(prefix='/api/issues', tags=['issues'])
md = MarkdownIt('commonmark', {'html': False, 'linkify': True, 'typographer': True}).enable('table')


def _read_markdown(markdown_path: str) -> str:
    path = (settings.content_root_path / markdown_path).resolve()
    if not path.exists() or settings.content_root_path not in path.parents:
        raise FileNotFoundError(markdown_path)
    return path.read_text(encoding='utf-8')


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
    markdown = _read_markdown(issue.markdown_path)
    return IssueDetail(**IssueListItem.model_validate(issue).model_dump(), markdown=markdown, html=md.render(markdown), markdown_path=issue.markdown_path)


@router.get('/{slug}', response_model=IssueDetail)
def get_issue(slug: str, db: Session = Depends(get_db)):
    issue = db.query(Issue).filter(Issue.slug == slug, Issue.is_published.is_(True)).first()
    if not issue:
        raise HTTPException(status_code=404, detail='Issue not found')
    try:
        markdown = _read_markdown(issue.markdown_path)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail='Issue content missing')
    return IssueDetail(**IssueListItem.model_validate(issue).model_dump(), markdown=markdown, html=md.render(markdown), markdown_path=issue.markdown_path)
