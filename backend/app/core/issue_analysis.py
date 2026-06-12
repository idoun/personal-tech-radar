from __future__ import annotations

import re
from dataclasses import dataclass


CATEGORY_KEYWORDS = {
    'AI Agent': ['agent', 'ai', 'llm', 'qwen', 'langgraph', 'mcp'],
    'LLM Serving': ['vllm', 'sglang', 'inference', 'serving', 'gpu'],
    'Security': ['security', 'sandbox', 'auth', 'ssh'],
    'DevTools': ['cli', 'terminal', 'devtools', 'editor', 'debug', 'tool'],
    'Infra / Cloud': ['cloud', 'server', 'infra', 'kubernetes', 'database'],
}


@dataclass
class ParsedArticleCard:
    title: str
    summary: str
    source: str | None = None
    geeknews: str | None = None


@dataclass
class IssueAnalysis:
    intro_lines: list[str]
    cards: list[ParsedArticleCard]

    @property
    def combined_text(self) -> str:
        parts = [*self.intro_lines]
        for card in self.cards:
            parts.append(card.title)
            if card.summary:
                parts.append(card.summary)
            if card.source:
                parts.append(card.source)
            if card.geeknews:
                parts.append(card.geeknews)
        return '\n'.join(part for part in parts if part).strip()

    def dominant_category(self) -> tuple[str, int]:
        scores = {category: 0 for category in CATEGORY_KEYWORDS}
        for index, card in enumerate(self.cards):
            text = f'{card.title} {card.summary}'.lower()
            weight = max(1, len(self.cards) - index)
            for category, keywords in CATEGORY_KEYWORDS.items():
                hits = sum(1 for keyword in keywords if keyword in text)
                if hits:
                    scores[category] += hits * weight

        best_category = 'Other'
        best_score = 0
        for category, score in scores.items():
            if score > best_score:
                best_category = category
                best_score = score
        return best_category, best_score

    def best_matching_card(self, keywords: list[str]) -> ParsedArticleCard | None:
        best_card = None
        best_score = 0
        for card in self.cards:
            text = f'{card.title} {card.summary}'.lower()
            score = sum(1 for keyword in keywords if keyword.lower() in text)
            if score > best_score:
                best_score = score
                best_card = card
        return best_card


CARD_HEADING_RE = re.compile(r'^##\s+(.+)$')


def parse_issue_markdown(markdown: str) -> IssueAnalysis:
    lines = markdown.splitlines()
    intro: list[str] = []
    cards: list[ParsedArticleCard] = []
    current: ParsedArticleCard | None = None

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        heading = CARD_HEADING_RE.match(line)
        if heading:
            if current:
                cards.append(current)
            raw_title = heading.group(1).strip()
            cleaned_title = raw_title.replace('🤖', '').strip()
            cleaned_title = re.sub(r'^\*\*(.+)\*\*$', r'\1', cleaned_title)
            current = ParsedArticleCard(title=cleaned_title, summary='')
            continue

        if current is None:
            if not line.startswith('오늘의 흐름:'):
                intro.append(line)
            continue

        if line.startswith('요약:'):
            current.summary = line.replace('요약:', '', 1).strip()
        elif line.startswith('- 원문:'):
            current.source = line.replace('- 원문:', '', 1).strip()
        elif line.startswith('- GeekNews:'):
            current.geeknews = line.replace('- GeekNews:', '', 1).strip()

    if current:
        cards.append(current)

    return IssueAnalysis(intro_lines=intro, cards=cards)
