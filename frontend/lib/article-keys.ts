export function normalizeArticleTitle(title: string) {
  const normalized = title.normalize('NFKC').trim().toLowerCase();
  const stripped = normalized
    .replace(/[^\p{L}\p{N}\s_-]+/gu, '')
    .replace(/[_\s-]+/g, '-')
    .replace(/^-+|-+$/g, '');
  return stripped || 'article';
}

export function buildArticleKey(issueSlug: string, articleTitle: string, articleIndex: number) {
  return `${issueSlug}::${normalizeArticleTitle(articleTitle)}::${Math.max(0, articleIndex)}`;
}

export function buildArticleDomId(articleKey: string) {
  return `article-${articleKey.replace(/[^a-zA-Z0-9_-]+/g, '-')}`;
}
