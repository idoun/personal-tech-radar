# Search Notes

This document describes the current `technews` search behavior that was added in the first lightweight search pass.

## Current UX

- The sidebar header contains a search input.
- When the query is empty, the normal archive view is shown:
  - `Top signals`
  - month groups
  - existing detail panel behavior
- When the query is non-empty, the sidebar switches into `search results` mode.
- Search results show:
  - title
  - issue date
  - matched field label
  - short snippet
- Clicking a result opens the existing detail view on the right.
- The active search term is highlighted in:
  - result titles
  - result snippets
  - detail title
  - summary / impact / reason / action items / tags / parsed article body

## Search scope

Current search is intentionally simple and does not use SQLite FTS yet.

Each published issue is checked against:

- `title`
- `short_summary`
- `impact_summary`
- `tags`
- `summary`
- `recommended_action`
- markdown body text

Markdown body text is normalized into plain text before matching so the first pass stays predictable and simple.

## Query behavior

- Query terms are split by whitespace.
- Matching is case-insensitive.
- Duplicate terms are removed.
- Terms are treated as OR matches for inclusion.
- Results become stronger when more terms match within the same field.

## Ranking

Results are sorted by a lightweight weighted score.

Field base weights:

- `title`: `120`
- `short_summary`: `90`
- `impact_summary`: `82`
- `tags`: `78`
- `summary`: `74`
- `recommended_action`: `68`
- `markdown`: `52`

Additional scoring rules:

- `+14` per matched search term within the best-matching field
- `+18` if all query terms appear in that field
- `+16` if the normalized full query string appears contiguously in that field
- small penalty when the first match appears later in the field text
- small recency bonus based on `issue_date`

Practical effect:

- title matches should usually outrank body-only matches
- short summary / impact summary / tag matches are favored over generic body matches
- body matches are still included, but lower priority

## Snippet generation

- Snippets are built from the best-matching field.
- Search tries to center the snippet near the first matched term.
- Leading or trailing ellipsis is added when content is trimmed.

## Why this version exists

This first pass intentionally avoids a heavier search stack.

Reasons:

- current archive size is still small enough for per-document scanning
- the existing archive UX is preserved
- search quality is good enough to validate the product need before adding complexity
- later migration to SQLite FTS5 remains possible without changing the basic UI model

## Likely future tuning points

- lower markdown weight if body matches feel too noisy
- raise tag/title weight if intent feels too topical
- promote `all terms matched` results more aggressively
- add lightweight caching for normalized markdown text if issue volume grows
- replace scan-based search with SQLite FTS5 if latency or corpus size demands it
