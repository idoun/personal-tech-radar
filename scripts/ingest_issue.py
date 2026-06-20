#!/usr/bin/env python3
import json
import sqlite3
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))

from app.core.config import settings
from app.core.profile import load_tech_radar_profile
from app.core.scoring import build_fallback_score
from app.core.summary import build_fallback_structured_summary

CONTENT_ROOT = settings.content_root_path
DB_PATH = settings.database_path


def _coerce_issue_date(value: str) -> date:
    return date.fromisoformat(value)


def _normalize_community_reaction(payload: dict) -> tuple[str, list[str]]:
    summary = str(payload.get('community_reaction_summary') or '').strip()[:160]
    bullets = [
        str(item).strip()
        for item in payload.get('community_reaction_bullets', [])
        if str(item).strip()
    ][:2]
    return summary, bullets


def main():
    payload = json.load(sys.stdin)
    issue_date = _coerce_issue_date(payload['issue_date'])
    title = payload['title']
    summary = payload['summary']
    markdown = payload['markdown'].strip() + '\n'
    community_reaction_summary, community_reaction_bullets = _normalize_community_reaction(payload)

    structured = build_fallback_structured_summary(summary, markdown=markdown)
    if payload.get('short_summary'):
        structured.short_summary = str(payload['short_summary']).strip() or structured.short_summary
    if payload.get('impact_summary'):
        structured.impact_summary = str(payload['impact_summary']).strip() or structured.impact_summary
    if payload.get('action_items'):
        structured.action_items = [str(item).strip() for item in payload['action_items'] if str(item).strip()] or structured.action_items
    if payload.get('tags'):
        structured.tags = [str(tag).strip() for tag in payload['tags'] if str(tag).strip()] or structured.tags
    if payload.get('radar_category'):
        structured.radar_category = str(payload['radar_category']).strip() or structured.radar_category
    if payload.get('radar_status'):
        structured.radar_status = str(payload['radar_status']).strip() or structured.radar_status

    score = build_fallback_score(title, structured, load_tech_radar_profile(), markdown=markdown)
    if payload.get('interest_score') is not None:
        score.interest_score = float(payload['interest_score'])
    if payload.get('project_score') is not None:
        score.project_score = float(payload['project_score'])
    if payload.get('novelty_score') is not None:
        score.novelty_score = float(payload['novelty_score'])
    if payload.get('actionability_score') is not None:
        score.actionability_score = float(payload['actionability_score'])
    if payload.get('credibility_score') is not None:
        score.credibility_score = float(payload['credibility_score'])
    if payload.get('community_score') is not None:
        score.community_score = float(payload['community_score'])
    if payload.get('final_score') is not None:
        score.final_score = float(payload['final_score'])
    if payload.get('score_reason'):
        score.reason = str(payload['score_reason']).strip() or score.reason
    if payload.get('recommended_action'):
        score.recommended_action = str(payload['recommended_action']).strip() or score.recommended_action
    slug = payload.get('slug') or issue_date.isoformat()
    rel_path = f'{issue_date.year:04d}/{issue_date.month:02d}/{slug}-geeknews.md'
    content_path = CONTENT_ROOT / rel_path
    content_path.parent.mkdir(parents=True, exist_ok=True)
    content_path.write_text(markdown, encoding='utf-8')

    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        '''INSERT INTO issues (
             slug, title, summary, short_summary, impact_summary, action_items_json, tags_json, radar_category, radar_status,
             interest_score, project_score, novelty_score, actionability_score, credibility_score, community_score, final_score,
             score_reason, recommended_action, community_reaction_summary, community_reaction_bullets_json,
             issue_date, year, month, markdown_path, is_published, created_at, updated_at
           )
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, datetime('now'), datetime('now'))
           ON CONFLICT(slug) DO UPDATE SET
             title=excluded.title,
             summary=excluded.summary,
             short_summary=excluded.short_summary,
             impact_summary=excluded.impact_summary,
             action_items_json=excluded.action_items_json,
             tags_json=excluded.tags_json,
             radar_category=excluded.radar_category,
             radar_status=excluded.radar_status,
             interest_score=excluded.interest_score,
             project_score=excluded.project_score,
             novelty_score=excluded.novelty_score,
             actionability_score=excluded.actionability_score,
             credibility_score=excluded.credibility_score,
             community_score=excluded.community_score,
             final_score=excluded.final_score,
             score_reason=excluded.score_reason,
             recommended_action=excluded.recommended_action,
             community_reaction_summary=excluded.community_reaction_summary,
             community_reaction_bullets_json=excluded.community_reaction_bullets_json,
             issue_date=excluded.issue_date,
             year=excluded.year,
             month=excluded.month,
             markdown_path=excluded.markdown_path,
             is_published=1,
             updated_at=datetime('now')''',
        (
            slug,
            title,
            summary,
            structured.short_summary,
            structured.impact_summary,
            json.dumps(structured.action_items, ensure_ascii=False),
            json.dumps(structured.tags, ensure_ascii=False),
            structured.radar_category,
            structured.radar_status,
            score.interest_score,
            score.project_score,
            score.novelty_score,
            score.actionability_score,
            score.credibility_score,
            score.community_score,
            score.final_score,
            score.reason,
            score.recommended_action,
            community_reaction_summary,
            json.dumps(community_reaction_bullets, ensure_ascii=False),
            issue_date.isoformat(),
            issue_date.year,
            issue_date.month,
            rel_path,
        ),
    )
    conn.commit()
    conn.close()
    print(json.dumps({'ok': True, 'slug': slug, 'markdown_path': rel_path}, ensure_ascii=False))


if __name__ == '__main__':
    main()
