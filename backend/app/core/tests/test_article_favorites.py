from datetime import date
from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from app.api.routes_issues import create_article_favorite, delete_article_favorite, list_article_favorites
from app.db.session import Base
from app.models.article_favorite import ArticleFavorite
from app.schemas.issue import ArticleFavoriteDeleteRequest, ArticleFavoriteUpsertRequest


def _make_session() -> Session:
    engine = create_engine('sqlite:///:memory:', connect_args={'check_same_thread': False})
    Base.metadata.create_all(bind=engine)
    return Session(engine)


def test_article_favorite_round_trip_is_scoped_per_user():
    db = _make_session()

    saved = create_article_favorite(
        ArticleFavoriteUpsertRequest(
            issue_slug='2026-06-19',
            issue_date=date(2026, 6, 19),
            article_title='Git에서 파일을 무시하는 방법은 .gitignore만이 아님',
            article_index=0,
        ),
        _user_id=7,
        db=db,
    )

    assert saved.issue_slug == '2026-06-19'
    assert saved.article_index == 0
    assert 'gitignore만이-아님' in saved.article_key

    listed = list_article_favorites(_user_id=7, db=db)
    assert len(listed) == 1
    assert listed[0].article_key == saved.article_key

    other_user_items = list_article_favorites(_user_id=8, db=db)
    assert other_user_items == []


def test_article_favorite_delete_is_idempotent():
    db = _make_session()
    create_article_favorite(
        ArticleFavoriteUpsertRequest(
            issue_slug='2026-06-19',
            issue_date=date(2026, 6, 19),
            article_title='로컬 Qwen은 더 나쁜 Opus가 아니라 다른 도구다',
            article_index=3,
        ),
        _user_id=11,
        db=db,
    )

    deleted = delete_article_favorite(
        ArticleFavoriteDeleteRequest(
            issue_slug='2026-06-19',
            article_title='로컬 Qwen은 더 나쁜 Opus가 아니라 다른 도구다',
            article_index=3,
        ),
        _user_id=11,
        db=db,
    )
    deleted_again = delete_article_favorite(
        ArticleFavoriteDeleteRequest(
            issue_slug='2026-06-19',
            article_title='로컬 Qwen은 더 나쁜 Opus가 아니라 다른 도구다',
            article_index=3,
        ),
        _user_id=11,
        db=db,
    )

    assert deleted.ok is True
    assert deleted_again.ok is True
    assert db.query(ArticleFavorite).count() == 0
