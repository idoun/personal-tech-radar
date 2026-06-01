from datetime import date
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

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
