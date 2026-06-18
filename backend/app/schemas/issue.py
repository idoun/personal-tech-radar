from datetime import date

from pydantic import BaseModel, Field, ConfigDict


class IssueScore(BaseModel):
    interest_score: float
    project_score: float
    novelty_score: float
    actionability_score: float
    credibility_score: float
    community_score: float
    final_score: float
    reason: str
    recommended_action: str


class IssueListItem(BaseModel):
    id: int
    slug: str
    title: str
    summary: str
    short_summary: str
    impact_summary: str
    action_items: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    radar_category: str
    radar_status: str
    score: IssueScore
    issue_date: date
    year: int
    month: int
    is_published: bool

    model_config = ConfigDict(from_attributes=True)


class DeliveryDecisionPayload(BaseModel):
    should_send: bool
    important: bool
    threshold: float
    important_threshold: float
    reason: str


class TelegramPreviewPayload(BaseModel):
    title: str
    body: str


class DeliveryPreviewPayload(BaseModel):
    article_slug: str
    channel: str
    decision: DeliveryDecisionPayload
    telegram: TelegramPreviewPayload


class DeliveryLogPayload(BaseModel):
    id: str
    article_slug: str
    channel: str
    status: str
    message: str
    sent_at: str | None
    error: str | None


class IssueDetail(IssueListItem):
    markdown: str
    html: str
    markdown_path: str
    community_reaction_summary: str = ''
    community_reaction_bullets: list[str] = Field(default_factory=list)
    delivery_preview: DeliveryPreviewPayload | None = None


class IssueGroupMonth(BaseModel):
    year: int
    month: int
    label: str
    items: list[IssueListItem]


class IssueSearchResult(IssueListItem):
    matched_field: str
    snippet: str
    matched_terms: list[str] = Field(default_factory=list)
    match_score: float


class IssueSearchResponse(BaseModel):
    query: str
    total: int
    items: list[IssueSearchResult]


class IssueIngestRequest(BaseModel):
    issue_date: date
    title: str
    summary: str
    markdown: str
    short_summary: str | None = None
    impact_summary: str | None = None
    action_items: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    radar_category: str | None = None
    radar_status: str | None = None
    interest_score: float | None = None
    project_score: float | None = None
    novelty_score: float | None = None
    actionability_score: float | None = None
    credibility_score: float | None = None
    community_score: float | None = None
    final_score: float | None = None
    score_reason: str | None = None
    recommended_action: str | None = None
    community_reaction_summary: str | None = None
    community_reaction_bullets: list[str] = Field(default_factory=list)
    slug: str | None = None
    is_published: bool = True


class IssueDeliveryLogRequest(BaseModel):
    channel: str = 'telegram'
    status: str
    message: str
    error: str | None = None
    sent_at: str | None = None


class IssueIngestResponse(BaseModel):
    ok: bool = True
    slug: str
    markdown_path: str
    created: bool
    issue: IssueDetail
