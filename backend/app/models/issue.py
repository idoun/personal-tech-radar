from datetime import datetime, date

from sqlalchemy import Boolean, Date, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Issue(Base):
    __tablename__ = 'issues'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    summary: Mapped[str] = mapped_column(Text)
    short_summary: Mapped[str] = mapped_column(Text, default='')
    impact_summary: Mapped[str] = mapped_column(Text, default='')
    action_items_json: Mapped[str] = mapped_column(Text, default='[]')
    tags_json: Mapped[str] = mapped_column(Text, default='[]')
    radar_category: Mapped[str] = mapped_column(String(64), default='Other')
    radar_status: Mapped[str] = mapped_column(String(32), default='Assess')
    interest_score: Mapped[float] = mapped_column(default=0.0)
    project_score: Mapped[float] = mapped_column(default=0.0)
    novelty_score: Mapped[float] = mapped_column(default=0.0)
    actionability_score: Mapped[float] = mapped_column(default=0.0)
    credibility_score: Mapped[float] = mapped_column(default=0.0)
    community_score: Mapped[float] = mapped_column(default=0.0)
    final_score: Mapped[float] = mapped_column(default=0.0, index=True)
    score_reason: Mapped[str] = mapped_column(Text, default='')
    recommended_action: Mapped[str] = mapped_column(Text, default='')
    community_reaction_summary: Mapped[str] = mapped_column(Text, default='')
    community_reaction_bullets_json: Mapped[str] = mapped_column(Text, default='[]')
    telegram_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    telegram_sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    telegram_message: Mapped[str] = mapped_column(Text, default='')
    telegram_error: Mapped[str] = mapped_column(Text, default='')
    issue_date: Mapped[date] = mapped_column(Date, index=True)
    year: Mapped[int] = mapped_column(Integer, index=True)
    month: Mapped[int] = mapped_column(Integer, index=True)
    markdown_path: Mapped[str] = mapped_column(String(255))
    is_published: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
