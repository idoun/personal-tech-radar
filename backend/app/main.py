from datetime import date
from pathlib import Path

import sqlite3

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_issues import router as issues_router
from app.core.config import settings
from app.db.session import Base, engine
from app.models.issue import Issue

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex='https?://.*',
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


def ensure_tables():
    db_path = settings.database_path
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path) as conn:
        existing = {row[1] for row in conn.execute("PRAGMA table_info(issues)")}
        migrations = {
            'short_summary': "ALTER TABLE issues ADD COLUMN short_summary TEXT NOT NULL DEFAULT ''",
            'impact_summary': "ALTER TABLE issues ADD COLUMN impact_summary TEXT NOT NULL DEFAULT ''",
            'action_items_json': "ALTER TABLE issues ADD COLUMN action_items_json TEXT NOT NULL DEFAULT '[]'",
            'tags_json': "ALTER TABLE issues ADD COLUMN tags_json TEXT NOT NULL DEFAULT '[]'",
            'radar_category': "ALTER TABLE issues ADD COLUMN radar_category TEXT NOT NULL DEFAULT 'Other'",
            'radar_status': "ALTER TABLE issues ADD COLUMN radar_status TEXT NOT NULL DEFAULT 'Assess'",
            'interest_score': "ALTER TABLE issues ADD COLUMN interest_score REAL NOT NULL DEFAULT 0",
            'project_score': "ALTER TABLE issues ADD COLUMN project_score REAL NOT NULL DEFAULT 0",
            'novelty_score': "ALTER TABLE issues ADD COLUMN novelty_score REAL NOT NULL DEFAULT 0",
            'actionability_score': "ALTER TABLE issues ADD COLUMN actionability_score REAL NOT NULL DEFAULT 0",
            'credibility_score': "ALTER TABLE issues ADD COLUMN credibility_score REAL NOT NULL DEFAULT 0",
            'community_score': "ALTER TABLE issues ADD COLUMN community_score REAL NOT NULL DEFAULT 0",
            'final_score': "ALTER TABLE issues ADD COLUMN final_score REAL NOT NULL DEFAULT 0",
            'score_reason': "ALTER TABLE issues ADD COLUMN score_reason TEXT NOT NULL DEFAULT ''",
            'recommended_action': "ALTER TABLE issues ADD COLUMN recommended_action TEXT NOT NULL DEFAULT ''",
            'telegram_sent': "ALTER TABLE issues ADD COLUMN telegram_sent BOOLEAN NOT NULL DEFAULT 0",
            'telegram_sent_at': "ALTER TABLE issues ADD COLUMN telegram_sent_at DATETIME",
            'telegram_message': "ALTER TABLE issues ADD COLUMN telegram_message TEXT NOT NULL DEFAULT ''",
            'telegram_error': "ALTER TABLE issues ADD COLUMN telegram_error TEXT NOT NULL DEFAULT ''",
        }
        for column, sql in migrations.items():
            if column not in existing:
                conn.execute(sql)
        conn.commit()

    Base.metadata.create_all(bind=engine)


def seed_if_empty():
    from sqlalchemy.orm import Session

    with Session(engine) as session:
        has_issue = session.query(Issue).first()
        if has_issue:
            return

        sample_path = settings.content_root_path / '2026/05/2026-05-24-geeknews.md'
        sample_path.parent.mkdir(parents=True, exist_ok=True)
        if not sample_path.exists():
            sample_path.write_text(
                '# GeekNews 어제자 요약\n\n'
                '오늘의 흐름: AI와 개발자 도구, 저수준 최적화 이야기가 함께 눈에 띔.\n\n'
                '## 1. **Codex, 활용 사례 모음 대폭 확장**\n'
                '- 요약: 코딩 보조를 넘어 엔지니어링 전반으로 유스케이스가 넓어지는 흐름을 보여줌.\n'
                '- 원문: https://developers.openai.com/codex/use-cases\n'
                '- GeekNews: https://news.hada.io/topic?id=29847\n\n'
                '## 2. microsoft/mimalloc - 고성능 범용 메모리 할당자\n'
                '- 요약: 기존 malloc 대체만으로 성능과 메모리 효율을 끌어올릴 수 있어 시스템 최적화 관점에서 다시 볼 만함.\n'
                '- 원문: https://github.com/microsoft/mimalloc\n'
                '- GeekNews: https://news.hada.io/topic?id=29812\n',
                encoding='utf-8',
            )

        issue = Issue(
            slug='2026-05-24',
            title='GeekNews 어제자 요약 - 2026-05-24',
            summary='AI, 개발자 도구, 저수준 최적화 흐름이 함께 보인 하루.',
            short_summary='AI, 개발자 도구, 저수준 최적화 흐름이 함께 보인 하루.',
            impact_summary='개발 도구와 시스템 최적화 흐름을 함께 파악할 수 있는 샘플 요약입니다.',
            action_items_json='["원문 링크를 검토하고 후속 실험 후보를 정리한다."]',
            tags_json='["GeekNews", "Sample"]',
            radar_category='Other',
            radar_status='Assess',
            interest_score=6.0,
            project_score=5.0,
            novelty_score=5.5,
            actionability_score=6.5,
            credibility_score=6.0,
            community_score=4.5,
            final_score=5.69,
            score_reason='샘플 데이터 기준의 기본 점수입니다.',
            recommended_action='원문 링크를 검토하고 후속 실험 후보를 정리한다.',
            telegram_sent=False,
            telegram_message='',
            telegram_error='',
            issue_date=date(2026, 5, 24),
            year=2026,
            month=5,
            markdown_path='2026/05/2026-05-24-geeknews.md',
            is_published=True,
        )
        session.add(issue)
        session.commit()


ensure_tables()
seed_if_empty()

app.include_router(issues_router)


@app.get('/')
def root():
    return {'service': settings.app_name, 'status': 'ok'}


@app.get('/health')
def health():
    return {'status': 'ok'}
