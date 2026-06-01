from datetime import date

from pydantic import BaseModel, Field


class IssueListItem(BaseModel):
    id: int
    slug: str
    title: str
    summary: str
    issue_date: date
    year: int
    month: int
    is_published: bool

    class Config:
        from_attributes = True


class IssueDetail(IssueListItem):
    markdown: str
    html: str
    markdown_path: str


class IssueGroupMonth(BaseModel):
    year: int
    month: int
    label: str
    items: list[IssueListItem]


class IssueIngestRequest(BaseModel):
    issue_date: date
    title: str
    summary: str
    markdown: str
    slug: str | None = None
    is_published: bool = True


class IssueIngestResponse(BaseModel):
    ok: bool = True
    slug: str
    markdown_path: str
    created: bool
    issue: IssueDetail
