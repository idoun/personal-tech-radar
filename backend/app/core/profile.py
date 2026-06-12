from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field, ValidationError

from app.core.config import settings


class ProjectProfile(BaseModel):
    name: str
    description: str = ''
    keywords: list[str] = Field(default_factory=list)


class TechRadarProfile(BaseModel):
    interests: list[str] = Field(default_factory=list)
    projects: list[ProjectProfile] = Field(default_factory=list)


class TechRadarProfileDocument(BaseModel):
    profile: TechRadarProfile


DEFAULT_TECH_RADAR_PROFILE = TechRadarProfile(
    interests=[
        'AI Systems',
        'DevTools',
        'ML Infrastructure',
        'Security',
        'Knowledge Retrieval',
    ],
    projects=[
        ProjectProfile(
            name='Workflow Automation Platform',
            description='Multi-step agent and workflow orchestration for backend automation',
            keywords=[
                'workflow orchestration',
                'workflow engine',
                'execution graph',
                'task graph',
                'tool routing',
                'agent runtime',
                'orchestration engine',
                'control plane',
            ],
        ),
        ProjectProfile(
            name='Observability and Replay Toolkit',
            description='Trace, replay, and debug tool-based AI or API execution',
            keywords=[
                'observability',
                'tracing',
                'prompt tracing',
                'execution trace',
                'session replay',
                'telemetry',
                'debugging',
                'provenance',
            ],
        ),
        ProjectProfile(
            name='Self-hosted Model Serving Stack',
            description='Private model serving and inference operations in local or controlled environments',
            keywords=[
                'self-hosted llm',
                'private llm',
                'model serving',
                'inference server',
                'local inference',
                'gpu serving',
                'quantization',
                'tensor parallel',
            ],
        ),
        ProjectProfile(
            name='Technical Content Feed',
            description='Summarization, ranking, and delivery of technical content streams',
            keywords=[
                'news digest',
                'personalized feed',
                'content ranking',
                'summarization pipeline',
                'content recommendation',
                'delivery workflow',
            ],
        ),
    ],
)


def _default_document() -> TechRadarProfileDocument:
    return TechRadarProfileDocument(profile=DEFAULT_TECH_RADAR_PROFILE.model_copy(deep=True))


def _resolve_profile_path(profile_path: str | None = None) -> Path:
    configured = profile_path or settings.tech_radar_profile_path
    path = Path(configured)
    if path.is_absolute():
        return path
    return (Path(__file__).resolve().parents[3] / path).resolve()


def load_tech_radar_profile(profile_path: str | None = None) -> TechRadarProfile:
    path = _resolve_profile_path(profile_path)
    if not path.exists():
        return _default_document().profile

    try:
        data = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
        document = TechRadarProfileDocument.model_validate(data)
    except (OSError, yaml.YAMLError, ValidationError):
        return _default_document().profile

    return document.profile
