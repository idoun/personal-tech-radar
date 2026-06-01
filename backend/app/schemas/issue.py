from datetime import date

from pydantic import BaseModel


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
