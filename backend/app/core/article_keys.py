from __future__ import annotations

import re
import unicodedata


def normalize_article_title(title: str) -> str:
    normalized = unicodedata.normalize('NFKC', title or '').strip().lower()
    normalized = re.sub(r'[^\w\s-]', '', normalized, flags=re.UNICODE)
    normalized = re.sub(r'[_\s-]+', '-', normalized, flags=re.UNICODE).strip('-')
    return normalized or 'article'


def build_article_key(issue_slug: str, article_title: str, article_index: int) -> str:
    safe_index = max(0, int(article_index))
    return f'{issue_slug}::{normalize_article_title(article_title)}::{safe_index}'
