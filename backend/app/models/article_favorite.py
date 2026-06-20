from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class ArticleFavorite(Base):
    __tablename__ = 'article_favorites'
    __table_args__ = (
        UniqueConstraint('user_id', 'issue_slug', 'article_key', name='uq_article_favorites_user_issue_key'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    issue_slug: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    issue_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    article_key: Mapped[str] = mapped_column(String(255), nullable=False)
    article_title: Mapped[str] = mapped_column(String(255), nullable=False)
    article_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
