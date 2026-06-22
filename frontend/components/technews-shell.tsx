'use client';

import { useEffect, useMemo, useState } from 'react';

import { addArticleFavorite, fetchArticleFavorites, fetchAuthSession, fetchIssue, fetchIssueGroups, fetchIssueSearch, fetchLatestIssue, loginWithPassword, logoutSharedSession, removeArticleFavorite } from '@/lib/api';
import { buildArticleDomId, buildArticleKey } from '@/lib/article-keys';
import type { ArticleFavorite, AuthUser, IssueDetail, IssueGroupMonth, IssueListItem, IssueSearchResult } from '@/lib/types';
import { TechNewsAuthForm } from './technews-auth-form';

type ThemeMode = 'dark' | 'light';

const THEME_STORAGE_KEY = 'technews-theme';
const RADAR_STATUS_GUIDE = [
  { label: 'Adopt', description: '이미 써볼 만하거나 바로 적용 후보인 상태' },
  { label: 'Trial', description: '짧은 실험이나 비교 검토를 권하는 상태' },
  { label: 'Assess', description: '지켜보며 맥락을 더 모으는 상태' },
  { label: 'Hold', description: '당장 우선순위는 낮게 두는 상태' },
] as const;

function formatLongDate(value: string) {
  const parsed = new Date(`${value}T00:00:00+09:00`);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  try {
    return new Intl.DateTimeFormat('ko-KR', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      weekday: 'short',
    }).format(parsed);
  } catch {
    return value;
  }
}

function monthLabel(year: number, month: number) {
  return `${year}년 ${month}월`;
}

function displayTitle(title: string) {
  return title.replace(/^((?:GeekNews)\s+)어제자\s+요약\s*-\s*/u, '$1').trim();
}

type ArticleCard = {
  title: string;
  summary: string;
  source?: string;
  geeknews?: string;
  communityReaction?: string;
  communityPoints: string[];
  ai: boolean;
};

type ArticleCardWithMeta = ArticleCard & {
  articleKey: string;
  articleIndex: number;
  domId: string;
};

function BookmarkIcon({ filled }: { filled: boolean }) {
  return (
    <svg viewBox="0 0 20 20" fill={filled ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="1.7" className="h-4 w-4">
      <path strokeLinecap="round" strokeLinejoin="round" d="M5.25 3.75h9.5a1 1 0 0 1 1 1v11.5l-5.75-3-5.75 3V4.75a1 1 0 0 1 1-1Z" />
    </svg>
  );
}

function buildTopSummary(detail: IssueDetail, _cards: ArticleCard[]) {
  return detail.short_summary || buildFallbackSummary(detail.summary);
}

function buildFallbackSummary(summary: string) {
  const normalized = summary.replace(/^오늘의 흐름:\s*/, '').trim();
  return normalized || '오늘의 주요 GeekNews 요약';
}

function parseIssueBody(markdown: string) {
  const lines = markdown.split(/\r?\n/);
  const intro: string[] = [];
  const cards: ArticleCard[] = [];
  let current: ArticleCard | null = null;

  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line) continue;

    const heading = line.match(/^##\s+(.+)$/);
    if (heading) {
      if (current) cards.push(current);
      const rawTitle = heading[1].trim();
      const cleanedTitle = rawTitle.replace(/^🤖\s*/, '').replace(/^\*\*(.+)\*\*$/, '$1').replace(/^\*\*(.+)\*\*$/, '$1');
      current = {
        title: cleanedTitle.replace(/^\*\*(.+)\*\*$/, '$1'),
        summary: '',
        communityPoints: [],
        ai: rawTitle.includes('🤖') || /\*\*/.test(rawTitle),
      };
      continue;
    }

    if (!current) {
      if (!line.startsWith('오늘의 흐름:')) {
        intro.push(line);
      }
      continue;
    }

    if (line.startsWith('요약:')) {
      current.summary = line.replace('요약:', '').trim();
    } else if (line.startsWith('- 댓글 반응:') || line.startsWith('- 커뮤니티 반응:')) {
      current.communityReaction = line.replace(/^- (댓글|커뮤니티) 반응:/, '').trim();
    } else if (line.startsWith('- 댓글 포인트:') || line.startsWith('- 커뮤니티 포인트:')) {
      const point = line.replace(/^- (댓글|커뮤니티) 포인트:/, '').trim();
      if (point) {
        current.communityPoints.push(point);
      }
    } else if (line.startsWith('- 원문:')) {
      current.source = line.replace('- 원문:', '').trim();
    } else if (line.startsWith('- GeekNews:')) {
      current.geeknews = line.replace('- GeekNews:', '').trim();
    }
  }

  if (current) cards.push(current);
  return { intro, cards };
}

function scoreTone(score: number) {
  if (score >= 8.5) return 'text-rose-200 bg-rose-500/15 border-rose-500/30';
  if (score >= 7) return 'text-amber-200 bg-amber-500/15 border-amber-500/30';
  return 'text-slate-200 bg-slate-800/80 border-slate-700';
}

function radarTone(status: string, theme: ThemeMode) {
  switch (status) {
    case 'Adopt':
      return theme === 'dark'
        ? 'text-emerald-100 bg-emerald-500/22 border-emerald-400/35'
        : 'text-emerald-800 bg-emerald-100 border-emerald-200';
    case 'Trial':
      return theme === 'dark'
        ? 'text-sky-50 bg-sky-400/24 border-sky-300/38'
        : 'text-sky-900 bg-sky-100 border-sky-200';
    case 'Assess':
      return theme === 'dark'
        ? 'text-amber-100 bg-amber-500/22 border-amber-400/35'
        : 'text-amber-900 bg-amber-100 border-amber-200';
    case 'Hold':
      return theme === 'dark'
        ? 'text-rose-100 bg-rose-500/22 border-rose-400/35'
        : 'text-rose-900 bg-rose-100 border-rose-200';
    default:
      return theme === 'dark'
        ? 'text-slate-100 bg-slate-800/90 border-slate-700'
        : 'text-slate-700 bg-slate-100 border-slate-200';
  }
}

function metricTone(score: number) {
  if (score >= 8.5) return 'bg-gradient-to-r from-rose-400 via-pink-400 to-orange-300';
  if (score >= 7) return 'bg-gradient-to-r from-amber-300 via-orange-300 to-rose-300';
  return 'bg-gradient-to-r from-slate-500 to-slate-400';
}

function guideChipTone(theme: ThemeMode) {
  return theme === 'dark'
    ? 'border-slate-700 bg-slate-900/80 text-slate-100'
    : 'border-slate-300 bg-white text-slate-800';
}

function importantChipTone(theme: ThemeMode) {
  return theme === 'dark'
    ? 'border-rose-500/30 bg-rose-500/15 text-rose-200'
    : 'border-rose-200 bg-rose-50 text-rose-700';
}

function getThemeClass(theme: ThemeMode) {
  if (theme === 'light') {
    return {
      app: 'bg-slate-100 text-slate-900',
      mobileOverlay: 'bg-slate-900/30',
      sidebar: 'border-slate-200 bg-white md:bg-white/96 md:backdrop-blur-2xl shadow-[0_20px_60px_rgba(15,23,42,0.08)]',
      sidebarHeaderBorder: 'border-slate-200',
      sidebarEyebrow: 'text-rose-600',
      title: 'text-slate-900',
      sub: 'text-slate-500',
      sub2: 'text-slate-400',
      sidePanel: 'border-slate-200 bg-white shadow-[0_12px_36px_rgba(15,23,42,0.05)]',
      sidePanelItem: 'border-slate-200 bg-slate-50 hover:border-rose-200 hover:bg-rose-50',
      monthItemIdle: 'border-transparent text-slate-700 hover:border-slate-200 hover:bg-slate-100',
      monthItemActive: 'border-rose-300 bg-rose-50 text-slate-900 shadow-[0_8px_24px_rgba(244,63,94,0.12)]',
      monthDivider: 'border-slate-200',
      topBar: 'border-slate-200 bg-white/88 backdrop-blur-xl',
      accentText: 'text-rose-600',
      mobileButton: 'border-slate-300 bg-white text-slate-700',
      article: 'border-slate-200 bg-white shadow-[0_24px_80px_rgba(15,23,42,0.08)]',
      error: 'border-rose-200 bg-rose-50 text-rose-700',
      summaryBox: 'border-rose-200 bg-rose-50',
      summaryEyebrow: 'text-rose-600',
      panel: 'border-slate-200 bg-slate-50',
      panelSoft: 'border-slate-200 bg-white',
      bodyText: 'text-slate-700',
      strongText: 'text-slate-900',
      pill: 'border-slate-300 bg-white text-slate-700',
      actionDot: 'bg-rose-100 text-rose-700',
      primaryLink: 'border-rose-200 bg-rose-50 text-rose-700 hover:bg-rose-100',
      secondaryLink: 'border-slate-300 bg-white text-slate-700 hover:bg-slate-100',
      modalOverlay: 'bg-slate-950/45',
      modal: 'border-slate-200 bg-white text-slate-900',
      themeCardIdle: 'border-slate-200 bg-slate-50 text-slate-700 hover:bg-slate-100',
      themeCardActive: 'border-rose-300 bg-rose-50 text-slate-900',
      ghostButton: 'border-slate-300 bg-white text-slate-700 hover:bg-slate-100',
      searchInput: 'border-slate-300 bg-slate-50 text-slate-900 placeholder:text-slate-400',
      searchMark: 'bg-amber-200 text-slate-900',
    };
  }

  return {
    app: 'bg-slate-950 text-slate-100',
    mobileOverlay: 'bg-slate-950/70',
    sidebar: 'border-slate-800 bg-slate-950 md:bg-slate-950/95 md:backdrop-blur-2xl',
    sidebarHeaderBorder: 'border-slate-800',
    sidebarEyebrow: 'text-sky-300',
    title: 'text-slate-50',
    sub: 'text-slate-400',
    sub2: 'text-slate-400',
    sidePanel: 'border-slate-800 bg-slate-900/60',
    sidePanelItem: 'border-slate-800 bg-slate-900/70 hover:bg-slate-800/80',
    monthItemIdle: 'border-transparent text-slate-300 hover:bg-slate-800/70',
    monthItemActive: 'border-sky-500/20 bg-sky-500/15 text-sky-100',
    monthDivider: 'border-slate-800',
    topBar: 'border-slate-800 bg-slate-950/90',
    accentText: 'text-sky-300',
    mobileButton: 'border-slate-700 bg-slate-900/80 text-slate-200',
    article: 'border-slate-800 bg-slate-900/70 shadow-2xl shadow-slate-950/40',
    error: 'border-rose-900 bg-rose-950/40 text-rose-200',
    summaryBox: 'border-sky-500/20 bg-sky-500/10',
    summaryEyebrow: 'text-sky-300',
    panel: 'border-slate-800 bg-slate-950/40',
    panelSoft: 'border-slate-800 bg-slate-950/50',
    bodyText: 'text-slate-300',
    strongText: 'text-slate-100',
    pill: 'border-slate-700 bg-slate-900/70 text-slate-200',
    actionDot: 'bg-sky-500/15 text-sky-200',
    primaryLink: 'border-sky-500/30 bg-sky-500/10 text-sky-200 hover:bg-sky-500/20',
    secondaryLink: 'border-slate-700 bg-slate-800/80 text-slate-200 hover:bg-slate-700',
    modalOverlay: 'bg-black/60',
    modal: 'border-slate-800 bg-slate-900 text-slate-100',
    themeCardIdle: 'border-slate-700 bg-slate-950 text-slate-300 hover:bg-slate-900',
    themeCardActive: 'border-sky-500/40 bg-sky-500/12 text-white',
    ghostButton: 'border-slate-700 bg-slate-900/80 text-slate-200 hover:bg-slate-800',
    searchInput: 'border-slate-700 bg-slate-900/80 text-slate-100 placeholder:text-slate-500',
    searchMark: 'bg-sky-300 text-slate-950',
  };
}

function buildTopItems(groups: IssueGroupMonth[]): IssueListItem[] {
  return groups
    .flatMap((group) => group.items)
    .sort((a, b) => b.score.final_score - a.score.final_score)
    .slice(0, 5);
}

function normalizeSearchTerms(query: string) {
  return Array.from(new Set(query.toLowerCase().split(/\s+/).map((term) => term.trim()).filter(Boolean)));
}

function escapeRegExp(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function splitHighlightedText(text: string, query: string) {
  const terms = normalizeSearchTerms(query);
  if (!terms.length) {
    return [{ text, matched: false }];
  }

  const pattern = new RegExp(`(${terms.map(escapeRegExp).join('|')})`, 'gi');
  return text.split(pattern).filter(Boolean).map((part) => ({
    text: part,
    matched: terms.some((term) => part.toLowerCase() === term),
  }));
}

function HighlightText({ text, query, markClassName }: { text: string; query: string; markClassName: string }) {
  const parts = splitHighlightedText(text, query);
  return (
    <>
      {parts.map((part, index) =>
        part.matched ? (
          <mark key={`${part.text}-${index}`} className={`rounded px-0.5 ${markClassName}`}>
            {part.text}
          </mark>
        ) : (
          <span key={`${part.text}-${index}`}>{part.text}</span>
        ),
      )}
    </>
  );
}

function matchedFieldLabel(field: string) {
  switch (field) {
    case 'title':
      return '제목';
    case 'short_summary':
      return '짧은 요약';
    case 'impact_summary':
      return '영향';
    case 'summary':
      return '요약';
    case 'tags':
      return '태그';
    case 'recommended_action':
      return '액션';
    case 'markdown':
      return '본문';
    default:
      return '문서';
  }
}

export function TechNewsShell() {
  const [sessionChecked, setSessionChecked] = useState(false);
  const [authUser, setAuthUser] = useState<AuthUser | null>(null);
  const [groups, setGroups] = useState<IssueGroupMonth[]>([]);
  const [active, setActive] = useState<IssueDetail | null>(null);
  const [favorites, setFavorites] = useState<ArticleFavorite[]>([]);
  const [favoritesExpanded, setFavoritesExpanded] = useState(false);
  const [favoritePendingKey, setFavoritePendingKey] = useState<string | null>(null);
  const [favoriteNotice, setFavoriteNotice] = useState<string | null>(null);
  const [pendingArticleKey, setPendingArticleKey] = useState<string | null>(null);
  const [searchInput, setSearchInput] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<IssueSearchResult[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [theme, setTheme] = useState<ThemeMode>('light');

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
    if (stored === 'dark' || stored === 'light') {
      setTheme(stored);
    }
  }, []);

  useEffect(() => {
    if (typeof document === 'undefined' || typeof window === 'undefined') return;
    document.documentElement.dataset.theme = theme;
    window.localStorage.setItem(THEME_STORAGE_KEY, theme);
  }, [theme]);

  function applyGroupedIssues(groupData: IssueGroupMonth[], latest: IssueDetail) {
    setGroups(groupData);
    setActive(latest);
    const initial: Record<string, boolean> = {};
    const latestKey = groupData[0] ? `${groupData[0].year}-${groupData[0].month}` : null;
    for (const group of groupData) {
      const key = `${group.year}-${group.month}`;
      initial[key] = key === latestKey;
    }
    setExpanded(initial);
  }

  useEffect(() => {
    async function loadIssueData() {
      try {
        const [groupData, latest, favoriteItems] = await Promise.all([fetchIssueGroups(), fetchLatestIssue(), fetchArticleFavorites()]);
        applyGroupedIssues(groupData, latest);
        setFavorites(favoriteItems);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : '불러오지 못했습니다.');
      } finally {
        setLoading(false);
      }
    }

    async function bootstrap() {
      try {
        const session = await fetchAuthSession();
        if (!session.authenticated || !session.user) {
          setAuthUser(null);
          setLoading(false);
          return;
        }
        if (typeof window !== 'undefined' && session.access_token) {
          window.localStorage.setItem('idounai_token', session.access_token);
        }
        setAuthUser(session.user);
        await loadIssueData();
      } catch {
        setAuthUser(null);
        setLoading(false);
      } finally {
        setSessionChecked(true);
      }
    }

    void bootstrap();
  }, []);

  useEffect(() => {
    const nextQuery = searchInput.trim();
    const timeoutId = window.setTimeout(() => {
      setSearchQuery(nextQuery);
    }, 180);

    return () => window.clearTimeout(timeoutId);
  }, [searchInput]);

  useEffect(() => {
    if (!authUser) {
      return;
    }

    if (!searchQuery) {
      setSearchResults([]);
      setSearchLoading(false);
      return;
    }

    let cancelled = false;
    setSearchLoading(true);
    void (async () => {
      try {
        const response = await fetchIssueSearch(searchQuery);
        if (!cancelled) {
          setSearchResults(response.items);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setSearchResults([]);
          setError(err instanceof Error ? err.message : '검색하지 못했습니다.');
        }
      } finally {
        if (!cancelled) {
          setSearchLoading(false);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [authUser, searchQuery]);

  async function handleOpen(slug: string) {
    try {
      const issue = await fetchIssue(slug);
      setActive(issue);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : '문서를 열지 못했습니다.');
    }
  }

  async function handleLogin(email: string, password: string) {
    setLoading(true);
    try {
      const loginResult = await loginWithPassword(email, password);
      if (typeof window !== 'undefined' && loginResult.access_token) {
        window.localStorage.setItem('idounai_token', loginResult.access_token);
      }
      const session = await fetchAuthSession();
      if (!session.authenticated || !session.user) {
        throw new Error('로그인 세션을 확인하지 못했습니다.');
      }
      setAuthUser(session.user);
      setError(null);
      const [groupData, latest, favoriteItems] = await Promise.all([fetchIssueGroups(), fetchLatestIssue(), fetchArticleFavorites()]);
      applyGroupedIssues(groupData, latest);
      setFavorites(favoriteItems);
    } finally {
      setLoading(false);
    }
  }

  async function handleLogout() {
    try {
      await logoutSharedSession();
    } catch {
      // ignore logout transport failures and still clear local UI state
    }
    setAuthUser(null);
    if (typeof window !== 'undefined') {
      window.localStorage.removeItem('idounai_token');
    }
    setGroups([]);
    setActive(null);
    setFavorites([]);
    setSearchInput('');
    setSearchQuery('');
    setSearchResults([]);
    setFavoritesExpanded(false);
    setFavoritePendingKey(null);
    setFavoriteNotice(null);
    setPendingArticleKey(null);
    setError(null);
    setLoading(false);
    setSettingsOpen(false);
    setMobileSidebarOpen(false);
  }

  const parsed = active ? parseIssueBody(active.markdown) : { intro: [], cards: [] };
  const articleCards = useMemo<ArticleCardWithMeta[]>(
    () =>
      active
        ? parsed.cards.map((card, index) => {
            const articleKey = buildArticleKey(active.slug, card.title, index);
            return {
              ...card,
              articleIndex: index,
              articleKey,
              domId: buildArticleDomId(articleKey),
            };
          })
        : [],
    [active, parsed.cards],
  );
  const favoriteKeySet = useMemo(() => new Set(favorites.map((item) => item.article_key)), [favorites]);
  const topSummary = active ? buildTopSummary(active, parsed.cards) : '';
  const topItems = useMemo(() => buildTopItems(groups), [groups]);
  const visibleFavorites = useMemo(() => favorites.slice(0, 10), [favorites]);
  const grouped = useMemo(
    () =>
      groups.map((group) => ({
        ...group,
        items: group.items.map((item) => ({
          ...item,
          derivedSummary: active?.slug === item.slug ? topSummary : item.short_summary || buildFallbackSummary(item.summary),
        })),
      })),
    [groups, active, topSummary],
  );
  const themeClass = getThemeClass(theme);
  const isSearchMode = searchQuery.length > 0;

  useEffect(() => {
    if (!favoriteNotice) {
      return;
    }
    const timeoutId = window.setTimeout(() => setFavoriteNotice(null), 1800);
    return () => window.clearTimeout(timeoutId);
  }, [favoriteNotice]);

  useEffect(() => {
    if (!pendingArticleKey) {
      return;
    }
    const element = document.getElementById(buildArticleDomId(pendingArticleKey));
    if (!element) {
      return;
    }
    element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    element.classList.add('ring-2', 'ring-rose-400', 'ring-offset-2', 'ring-offset-transparent');
    const timeoutId = window.setTimeout(() => {
      element.classList.remove('ring-2', 'ring-rose-400', 'ring-offset-2', 'ring-offset-transparent');
      setPendingArticleKey(null);
    }, 1800);
    return () => window.clearTimeout(timeoutId);
  }, [articleCards, pendingArticleKey]);

  async function handleToggleFavorite(card: ArticleCardWithMeta) {
    if (!active) {
      return;
    }

    setFavoritePendingKey(card.articleKey);
    try {
      if (favoriteKeySet.has(card.articleKey)) {
        await removeArticleFavorite({
          issue_slug: active.slug,
          article_title: card.title,
          article_index: card.articleIndex,
        });
        setFavorites((prev) => prev.filter((item) => item.article_key !== card.articleKey));
        setFavoriteNotice('즐겨찾기에서 제거됨');
      } else {
        const saved = await addArticleFavorite({
          issue_slug: active.slug,
          issue_date: active.issue_date,
          article_title: card.title,
          article_index: card.articleIndex,
        });
        setFavorites((prev) => [saved, ...prev.filter((item) => item.article_key !== saved.article_key)]);
        setFavoritesExpanded(true);
        setFavoriteNotice('즐겨찾기에 저장됨');
      }
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : '즐겨찾기를 저장하지 못했습니다.');
    } finally {
      setFavoritePendingKey(null);
    }
  }

  async function handleOpenFavorite(item: ArticleFavorite) {
    setPendingArticleKey(item.article_key);
    setMobileSidebarOpen(false);
    if (active?.slug === item.issue_slug) {
      return;
    }
    await handleOpen(item.issue_slug);
  }

  if (!sessionChecked || (!authUser && loading)) {
    return <div className={`flex min-h-screen items-center justify-center ${themeClass.app}`}><div className={themeClass.sub}>세션 확인 중...</div></div>;
  }

  if (!authUser) {
    return <TechNewsAuthForm onSubmit={handleLogin} />;
  }

  return (
    <div className={`flex h-screen overflow-hidden ${themeClass.app}`}>
      {mobileSidebarOpen ? (
        <button
          type="button"
          aria-label="목록 닫기"
          className={`fixed inset-0 z-30 md:hidden ${themeClass.mobileOverlay}`}
          onClick={() => setMobileSidebarOpen(false)}
        />
      ) : null}

      <aside
        className={`fixed inset-y-0 left-0 z-40 flex h-dvh w-[308px] shrink-0 flex-col border-r transition-transform md:static md:h-screen md:translate-x-0 ${themeClass.sidebar} ${
          mobileSidebarOpen ? 'translate-x-0' : '-translate-x-full'
        } md:flex`}
      >
        <div className={`border-b px-4 py-4 ${themeClass.sidebarHeaderBorder}`}>
          <div className={`text-[11px] uppercase tracking-[0.24em] ${themeClass.sidebarEyebrow}`}>TechNews</div>
          <h1 className={`mt-1.5 text-xl font-semibold ${themeClass.title}`}>Personal Tech Radar</h1>
          <p className={`mt-1.5 text-[15px] leading-6 md:text-sm ${themeClass.sub}`}>중요도, 레이더 상태, 액션을 중심으로 GeekNews를 쌓아보는 공간</p>
          <div className="mt-4 flex items-center gap-2">
            <input
              type="search"
              value={searchInput}
              onChange={(event) => setSearchInput(event.target.value)}
              placeholder="제목, 요약, 본문 검색"
              className={`min-w-0 flex-1 rounded-xl border px-3 py-2 text-sm outline-none ${themeClass.searchInput}`}
            />
            {searchInput ? (
              <button
                type="button"
                className={`rounded-xl border px-3 py-2 text-xs ${themeClass.ghostButton}`}
                onClick={() => setSearchInput('')}
              >
                지우기
              </button>
            ) : null}
          </div>
          <div className={`mt-2 text-xs ${themeClass.sub}`}>
            {searchLoading ? '검색 중...' : isSearchMode ? `검색어: ${searchQuery}` : '검색어를 입력하면 결과 리스트로 전환됩니다.'}
          </div>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto px-2.5 py-2.5">
          {!isSearchMode ? (
            <div className={`mb-2.5 rounded-xl border ${themeClass.sidePanel}`}>
              <button
                type="button"
                onClick={() => setFavoritesExpanded((prev) => !prev)}
                className="flex w-full items-center justify-between px-3 py-2 text-left"
              >
                <span className={`text-[15px] font-medium md:text-sm ${themeClass.strongText}`}>즐겨찾기 {favorites.length}</span>
                <span className={`text-xs ${themeClass.sub}`}>{favoritesExpanded ? '접기' : '펼치기'}</span>
              </button>
              {favoritesExpanded ? (
                <div className={`border-t px-1.5 py-1 ${themeClass.monthDivider}`}>
                  {visibleFavorites.length ? (
                    visibleFavorites.map((item) => {
                      const activeCard = active?.slug === item.issue_slug && pendingArticleKey === item.article_key;
                      return (
                        <button
                          key={`favorite-${item.id}`}
                          type="button"
                          onClick={() => {
                            void handleOpenFavorite(item);
                          }}
                          className={`mb-1 w-full rounded-lg border px-3 py-2 text-left transition ${activeCard ? themeClass.monthItemActive : themeClass.sidePanelItem}`}
                        >
                          <div className="flex items-center justify-between gap-2">
                            <div className={`text-xs ${themeClass.sub}`}>{formatLongDate(item.issue_date)}</div>
                            <span className={`rounded-full border px-2 py-0.5 text-[11px] ${themeClass.pill}`}>저장됨</span>
                          </div>
                          <div className={`mt-1 line-clamp-2 text-[15px] font-medium md:text-sm ${themeClass.strongText}`}>{item.article_title}</div>
                        </button>
                      );
                    })
                  ) : (
                    <div className={`px-3 py-5 text-sm ${themeClass.sub}`}>저장한 기사가 아직 없습니다.</div>
                  )}
                </div>
              ) : null}
            </div>
          ) : null}
          {isSearchMode ? (
            <div className={`mb-2.5 rounded-xl border ${themeClass.sidePanel}`}>
              <div className={`border-b px-3 py-2 text-xs uppercase tracking-[0.2em] ${themeClass.monthDivider} ${themeClass.sub}`}>
                검색 결과 {searchLoading ? '' : `${searchResults.length}건`}
              </div>
              <div className="px-1.5 py-1">
                {!searchLoading && searchResults.length === 0 ? (
                  <div className={`px-3 py-6 text-sm ${themeClass.sub}`}>검색 결과가 없습니다.</div>
                ) : null}
                {searchResults.map((item) => {
                  const activeSlug = active?.slug === item.slug;
                  return (
                    <button
                      key={`search-${item.slug}`}
                      type="button"
                      onClick={() => {
                        setMobileSidebarOpen(false);
                        void handleOpen(item.slug);
                      }}
                      className={`mb-1 w-full rounded-lg border px-3 py-2 text-left transition ${activeSlug ? themeClass.monthItemActive : themeClass.sidePanelItem}`}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <div className={`text-xs ${themeClass.sub}`}>{formatLongDate(item.issue_date)}</div>
                        <div className={`rounded-full border px-2 py-0.5 text-[11px] font-semibold ${themeClass.pill}`}>
                          {matchedFieldLabel(item.matched_field)}
                        </div>
                      </div>
                      <div className={`mt-1 line-clamp-2 text-[15px] font-medium md:text-sm ${activeSlug ? '' : themeClass.strongText}`}>
                        <HighlightText text={displayTitle(item.title)} query={searchQuery} markClassName={themeClass.searchMark} />
                      </div>
                      <div className={`mt-1 line-clamp-3 text-[13px] leading-5 md:text-xs ${themeClass.sub}`}>
                        <HighlightText text={item.snippet} query={searchQuery} markClassName={themeClass.searchMark} />
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          ) : (
            <div className={`mb-2.5 rounded-xl border ${themeClass.sidePanel}`}>
              <div className={`border-b px-3 py-2 text-xs uppercase tracking-[0.2em] ${themeClass.monthDivider} ${themeClass.sub}`}>Top signals</div>
              <div className="px-1.5 py-1">
                {topItems.map((item, index) => (
                  <button
                    key={`top-${item.slug}`}
                    type="button"
                    onClick={() => {
                      setMobileSidebarOpen(false);
                      void handleOpen(item.slug);
                    }}
                    className={`mb-1 w-full rounded-lg border px-3 text-left ${themeClass.sidePanelItem} ${index < 2 ? 'py-2.5' : 'py-2'} md:py-2.5`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className={`line-clamp-1 text-[15px] font-medium md:text-sm ${themeClass.strongText}`}>{displayTitle(item.title)}</span>
                      <span className={`shrink-0 rounded-full border px-2 py-0.5 text-[11px] font-semibold ${scoreTone(item.score.final_score)}`}>
                        {item.score.final_score.toFixed(1)}
                      </span>
                    </div>
                    <div className={`mt-1 line-clamp-2 text-xs leading-5 md:line-clamp-2 md:text-[11px] ${themeClass.sub}`}>{item.short_summary}</div>
                  </button>
                ))}
              </div>
            </div>
          )}
          {!isSearchMode ? grouped.map((group) => {
            const key = `${group.year}-${group.month}`;
            const isExpanded = expanded[key] ?? false;
            return (
              <div key={key} className={`mb-2.5 rounded-xl border ${themeClass.sidePanel}`}>
                <button
                  type="button"
                  onClick={() => setExpanded((prev) => ({ ...prev, [key]: !isExpanded }))}
                  className="flex w-full items-center justify-between px-3 py-2 text-left"
                >
                  <span className={`text-[15px] font-medium md:text-sm ${themeClass.strongText}`}>{monthLabel(group.year, group.month)}</span>
                  <span className={`text-xs ${themeClass.sub}`}>{isExpanded ? '접기' : '펼치기'}</span>
                </button>
                {isExpanded ? (
                  <div className={`border-t px-1.5 py-1 ${themeClass.monthDivider}`}>
                    {group.items.map((item) => {
                      const activeSlug = active?.slug === item.slug;
                      return (
                        <button
                          key={item.slug}
                          type="button"
                          onClick={() => {
                            setMobileSidebarOpen(false);
                            void handleOpen(item.slug);
                          }}
                          className={`mb-1 w-full rounded-lg border px-3 py-2 text-left transition ${activeSlug ? themeClass.monthItemActive : themeClass.monthItemIdle}`}
                        >
                          <div className="flex items-center justify-between gap-2">
                            <div className={`text-xs ${themeClass.sub}`}>{formatLongDate(item.issue_date)}</div>
                            <div className={`rounded-full border px-2 py-0.5 text-[11px] font-semibold ${scoreTone(item.score.final_score)}`}>
                              {item.score.final_score.toFixed(1)}
                            </div>
                          </div>
                          <div className={`mt-1 line-clamp-2 text-[15px] font-medium md:text-sm ${activeSlug ? '' : themeClass.strongText}`}>{displayTitle(item.title)}</div>
                          <div className={`mt-1 line-clamp-2 text-[13px] leading-5 md:text-xs ${themeClass.sub}`}>{item.derivedSummary}</div>
                        </button>
                      );
                    })}
                  </div>
                ) : null}
              </div>
            );
          }) : null}
        </div>
      </aside>

      <main className="flex min-w-0 flex-1 flex-col overflow-y-auto">
        <div className={`border-b px-3 py-3 md:px-4 ${themeClass.topBar}`}>
          <div className="flex items-center justify-between gap-3">
            <div className={`text-xs uppercase tracking-[0.24em] ${themeClass.accentText}`}>Published brief</div>
            <div className="flex items-center gap-2">
              <div className={`hidden text-xs md:block ${themeClass.sub}`}>{authUser.email}</div>
              <button
                type="button"
                className={`inline-flex items-center rounded-full border px-3 py-1 text-xs md:hidden ${themeClass.mobileButton}`}
                onClick={() => setMobileSidebarOpen(true)}
              >
                목록 보기
              </button>
              <button
                type="button"
                className={`inline-flex items-center rounded-full border px-3 py-1 text-xs ${themeClass.ghostButton}`}
                onClick={() => setSettingsOpen(true)}
              >
                설정
              </button>
              <button
                type="button"
                className={`inline-flex items-center rounded-full border px-3 py-1 text-xs ${themeClass.ghostButton}`}
                onClick={() => {
                  void handleLogout();
                }}
              >
                로그아웃
              </button>
            </div>
          </div>
          <h2 className={`mt-1.5 text-[1.7rem] font-semibold leading-tight md:text-2xl ${themeClass.title}`}>
            {active ? <HighlightText text={displayTitle(active.title)} query={searchQuery} markClassName={themeClass.searchMark} /> : 'GeekNews Daily Summary'}
          </h2>
          <p className={`mt-1.5 text-[15px] md:text-sm ${themeClass.sub}`}>{active ? formatLongDate(active.issue_date) : '문서를 고르는 중'}</p>
        </div>

        <div className="mx-auto w-full max-w-[104rem] flex-1 px-2 py-3 md:max-w-[88rem] md:px-3 lg:max-w-[92rem] xl:max-w-[96rem] md:py-4">
          {loading ? <div className={themeClass.sub}>불러오는 중...</div> : null}
          {error ? <div className={`rounded-xl border px-4 py-3 text-[15px] md:text-sm ${themeClass.error}`}>{error}</div> : null}
          {!loading && active ? (
            <article className={`space-y-2.5 rounded-2xl border p-3.5 md:space-y-3 md:p-4 ${themeClass.article}`}>
              <section className={`rounded-xl border px-3.5 py-3 md:px-4 ${themeClass.panel}`}>
                <div className="flex flex-wrap items-center gap-2">
                  <div className={`text-[11px] font-semibold uppercase tracking-[0.2em] ${themeClass.sub}`}>읽는 법</div>
                  <span className={`rounded-full border px-2.5 py-1 text-xs font-medium ${guideChipTone(theme)}`}>🤖 AI/에이전트 관련 기사</span>
                  <span className={`rounded-full border px-2.5 py-1 text-xs font-medium ${scoreTone(active.score.final_score)}`}>중요도 0-10</span>
                  <span className={`rounded-full border px-2.5 py-1 text-xs font-medium ${radarTone(active.radar_status, theme)}`}>Radar 상태</span>
                  {active.delivery_preview?.decision.important ? (
                    <span className={`rounded-full border px-2.5 py-1 text-xs font-medium ${importantChipTone(theme)}`}>중요 알림 후보</span>
                  ) : null}
                </div>
                <div className={`mt-2 grid gap-2 text-[15px] leading-[1.6] md:grid-cols-2 md:text-sm ${themeClass.bodyText}`}>
                  <p>중요도는 내 관심사와 프로젝트 키워드, 실험 가능성까지 반영한 개인 기준 점수야.</p>
                  <p>중요 알림 후보는 중요도가 높아서 텔레그램 같은 빠른 채널로 따로 보낼 만한 글이라는 뜻이야.</p>
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {RADAR_STATUS_GUIDE.map((item) => (
                    <div key={item.label} className={`rounded-xl border px-3 py-2 text-sm ${themeClass.panelSoft}`}>
                      <div className="flex items-center gap-2">
                        <span className={`rounded-full border px-2 py-0.5 text-[11px] font-semibold ${radarTone(item.label, theme)}`}>{item.label}</span>
                        <span className={themeClass.bodyText}>{item.description}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </section>

              <div className="grid gap-2 lg:grid-cols-[1.45fr_0.95fr]">
                <div className={`rounded-xl border px-3.5 py-2.5 md:px-4 ${themeClass.summaryBox}`}>
                  <div className={`text-[11px] font-semibold uppercase tracking-[0.2em] ${themeClass.summaryEyebrow}`}>10초 요약</div>
                  <div className={`mt-1 max-w-3xl text-[15px] font-medium leading-[1.55] md:text-[15px] ${themeClass.strongText}`}>
                    <HighlightText text={topSummary} query={searchQuery} markClassName={themeClass.searchMark} />
                  </div>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${scoreTone(active.score.final_score)}`}>
                      중요도 {active.score.final_score.toFixed(1)}
                    </span>
                    <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${radarTone(active.radar_status, theme)}`}>
                      {active.radar_category} · {active.radar_status}
                    </span>
                    {active.delivery_preview?.decision.important ? (
                      <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${importantChipTone(theme)}`}>중요 알림 후보</span>
                    ) : null}
                  </div>
                </div>

                <div className={`rounded-xl border px-3.5 py-2.5 md:px-4 ${themeClass.panel}`}>
                  <div className={`text-[11px] font-semibold uppercase tracking-[0.2em] ${themeClass.sub}`}>왜 중요한가</div>
                  <p className={`mt-1.5 text-[15px] leading-[1.6] md:text-sm ${theme === 'dark' ? 'text-slate-200' : 'text-slate-700'}`}>
                    <HighlightText text={active.impact_summary} query={searchQuery} markClassName={themeClass.searchMark} />
                  </p>
                  <div className={`mt-2 text-[11px] uppercase tracking-[0.2em] ${themeClass.sub}`}>점수 근거</div>
                  <p className={`mt-1 text-[15px] leading-[1.6] md:text-sm ${themeClass.bodyText}`}>
                    <HighlightText text={active.score.reason} query={searchQuery} markClassName={themeClass.searchMark} />
                  </p>
                </div>
              </div>

              <div className="grid gap-2 lg:grid-cols-[1.1fr_0.95fr]">
                <section className={`rounded-xl border p-3.5 md:p-4 ${themeClass.panel}`}>
                  <div className={`text-[11px] font-semibold uppercase tracking-[0.2em] ${themeClass.sub}`}>Action</div>
                  <ol className={`mt-2 space-y-1.5 text-[15px] leading-[1.55] md:text-sm ${theme === 'dark' ? 'text-slate-200' : 'text-slate-700'}`}>
                    {active.action_items.map((item, index) => (
                      <li key={`${item}-${index}`} className="flex gap-2">
                        <span className={`mt-0.5 inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-semibold ${themeClass.actionDot}`}>{index + 1}</span>
                        <span><HighlightText text={item} query={searchQuery} markClassName={themeClass.searchMark} /></span>
                      </li>
                    ))}
                  </ol>
                </section>

                <section className={`rounded-xl border p-3.5 md:p-4 ${themeClass.panel}`}>
                  <div className={`text-[11px] font-semibold uppercase tracking-[0.2em] ${themeClass.sub}`}>Score breakdown</div>
                  <div className={`mt-2 space-y-1.5 text-[15px] md:text-sm ${theme === 'dark' ? 'text-slate-200' : 'text-slate-700'}`}>
                    {[
                      ['Interest', active.score.interest_score],
                      ['Project', active.score.project_score],
                      ['Novelty', active.score.novelty_score],
                      ['Actionability', active.score.actionability_score],
                      ['Credibility', active.score.credibility_score],
                      ['Community', active.score.community_score],
                    ].map(([label, value]) => (
                      <div key={String(label)}>
                        <div className={`mb-1 flex items-center justify-between text-xs ${themeClass.sub}`}>
                          <span>{label}</span>
                          <span>{Number(value).toFixed(1)}</span>
                        </div>
                        <div className={`h-2 rounded-full ${theme === 'dark' ? 'bg-slate-800' : 'bg-slate-200'}`}>
                          <div className={`h-2 rounded-full ${metricTone(Number(value))}`} style={{ width: `${Math.min(100, (Number(value) / 10) * 100)}%` }} />
                        </div>
                      </div>
                    ))}
                    <div className={`mt-2 rounded-lg border px-3 py-1.5 ${themeClass.pill}`}>
                      <div className={`text-xs ${themeClass.sub}`}>추천 다음 액션</div>
                      <div className={`mt-0.5 text-[15px] font-medium md:text-sm ${themeClass.strongText}`}>
                        <HighlightText text={active.score.recommended_action} query={searchQuery} markClassName={themeClass.searchMark} />
                      </div>
                    </div>
                  </div>
                </section>
              </div>

              {active.tags.length ? (
                <div className={`rounded-xl border px-3.5 py-2.5 md:px-4 ${themeClass.panel}`}>
                  <div className={`text-[11px] font-semibold uppercase tracking-[0.2em] ${themeClass.sub}`}>Tags</div>
                  <div className="mt-1.5 flex flex-wrap gap-1.5">
                    {active.tags.map((tag) => (
                      <span key={tag} className={`rounded-full border px-3 py-1 text-xs ${themeClass.pill}`}>
                        <HighlightText text={tag} query={searchQuery} markClassName={themeClass.searchMark} />
                      </span>
                    ))}
                  </div>
                </div>
              ) : null}

              {active.community_reaction_summary || active.community_reaction_bullets.length ? (
                <section className={`rounded-xl border px-3.5 py-2.5 md:px-4 ${themeClass.panelSoft}`}>
                  <div className={`text-[11px] font-semibold uppercase tracking-[0.2em] ${themeClass.sub}`}>커뮤니티 반응</div>
                  {active.community_reaction_summary ? (
                    <p className={`mt-1.5 text-[15px] leading-[1.65] md:text-sm ${themeClass.bodyText}`}>
                      <HighlightText text={active.community_reaction_summary} query={searchQuery} markClassName={themeClass.searchMark} />
                    </p>
                  ) : null}
                  {active.community_reaction_bullets.length ? (
                    <ul className={`mt-2 space-y-1.5 text-[15px] leading-[1.6] md:text-sm ${themeClass.bodyText}`}>
                      {active.community_reaction_bullets.map((item, index) => (
                        <li key={`${item}-${index}`} className="flex gap-2">
                          <span className={`mt-[0.45rem] h-1.5 w-1.5 shrink-0 rounded-full ${theme === 'dark' ? 'bg-slate-400' : 'bg-slate-500'}`} />
                          <span>
                            <HighlightText text={item} query={searchQuery} markClassName={themeClass.searchMark} />
                          </span>
                        </li>
                      ))}
                    </ul>
                  ) : null}
                </section>
              ) : null}

              {parsed.intro.length > 0 ? (
                <div className={`space-y-1.5 rounded-xl border px-3.5 py-2.5 text-[15px] leading-[1.65] md:px-4 ${themeClass.panel} ${themeClass.bodyText}`}>
                  {parsed.intro.map((line, index) => (
                    <p key={`${line}-${index}`}><HighlightText text={line} query={searchQuery} markClassName={themeClass.searchMark} /></p>
                  ))}
                </div>
              ) : null}

              <div className="space-y-2">
                {articleCards.map((card) => {
                  const isFavorite = favoriteKeySet.has(card.articleKey);
                  const isFavoriteBusy = favoritePendingKey === card.articleKey;
                  return (
                  <section
                    key={card.articleKey}
                    id={card.domId}
                    className={`scroll-mt-20 rounded-xl border p-3.5 md:p-4 ${isFavorite ? 'border-rose-300/60' : ''} ${themeClass.panelSoft}`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <h3 className={`min-w-0 text-[1.1rem] font-semibold leading-6 md:text-[1.15rem] md:leading-7 ${themeClass.title}`}>
                        {card.ai ? <span className="mr-2">🤖</span> : null}
                        <span className={card.ai ? 'font-bold' : ''}>
                          <HighlightText text={card.title} query={searchQuery} markClassName={themeClass.searchMark} />
                        </span>
                      </h3>
                      <button
                        type="button"
                        disabled={isFavoriteBusy}
                        onClick={() => {
                          void handleToggleFavorite(card);
                        }}
                        className={`inline-flex shrink-0 items-center gap-1 rounded-full border px-2.5 py-1 text-xs font-medium transition ${
                          isFavorite
                            ? theme === 'dark'
                              ? 'border-rose-400/50 bg-rose-500/15 text-rose-100'
                              : 'border-rose-300 bg-rose-50 text-rose-700'
                            : themeClass.ghostButton
                        } ${isFavoriteBusy ? 'opacity-70' : ''}`}
                        aria-label={isFavorite ? '즐겨찾기 제거' : '즐겨찾기 저장'}
                      >
                        <BookmarkIcon filled={isFavorite} />
                        <span>{isFavorite ? '저장됨' : '저장'}</span>
                      </button>
                    </div>
                    <p className={`mt-1.5 text-[15px] leading-[1.65] ${themeClass.bodyText}`}>
                      <HighlightText text={card.summary} query={searchQuery} markClassName={themeClass.searchMark} />
                    </p>
                    {card.communityReaction || card.communityPoints.length ? (
                      <div className={`mt-3 rounded-xl border px-3 py-2.5 ${themeClass.panel}`}>
                        <div className={`text-[11px] font-semibold uppercase tracking-[0.18em] ${themeClass.sub}`}>댓글 반응</div>
                        {card.communityReaction ? (
                          <p className={`mt-1.5 text-[15px] leading-[1.65] ${themeClass.bodyText}`}>
                            <HighlightText text={card.communityReaction} query={searchQuery} markClassName={themeClass.searchMark} />
                          </p>
                        ) : null}
                        {card.communityPoints.length ? (
                          <ul className={`mt-2 space-y-1.5 text-[15px] leading-[1.6] md:text-sm ${themeClass.bodyText}`}>
                            {card.communityPoints.map((item, itemIndex) => (
                              <li key={`${item}-${itemIndex}`} className="flex gap-2">
                                <span className={`mt-[0.45rem] h-1.5 w-1.5 shrink-0 rounded-full ${theme === 'dark' ? 'bg-slate-400' : 'bg-slate-500'}`} />
                                <span>
                                  <HighlightText text={item} query={searchQuery} markClassName={themeClass.searchMark} />
                                </span>
                              </li>
                            ))}
                          </ul>
                        ) : null}
                      </div>
                    ) : null}
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {card.source ? (
                        <a
                          href={card.source}
                          target="_blank"
                          rel="noreferrer"
                          className={`rounded-full border px-3 py-1 text-[15px] transition md:text-sm ${themeClass.primaryLink}`}
                        >
                          원문 보기
                        </a>
                      ) : null}
                      {card.geeknews ? (
                        <a
                          href={card.geeknews}
                          target="_blank"
                          rel="noreferrer"
                          className={`rounded-full border px-3 py-1 text-[15px] transition md:text-sm ${themeClass.secondaryLink}`}
                        >
                          GeekNews 글 보기
                        </a>
                      ) : null}
                    </div>
                  </section>
                );})}
              </div>
            </article>
          ) : null}
        </div>
      </main>

      {favoriteNotice ? (
        <div className="pointer-events-none fixed right-4 top-4 z-50">
          <div className={`rounded-full border px-4 py-2 text-sm shadow-lg ${theme === 'dark' ? 'border-rose-400/35 bg-slate-900 text-rose-100' : 'border-rose-200 bg-white text-rose-700'}`}>
            {favoriteNotice}
          </div>
        </div>
      ) : null}

      {settingsOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center px-4">
          <button
            type="button"
            aria-label="설정 닫기"
            className={`absolute inset-0 ${themeClass.modalOverlay}`}
            onClick={() => setSettingsOpen(false)}
          />
          <div className={`relative w-full max-w-md rounded-3xl border p-6 shadow-2xl ${themeClass.modal}`}>
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className={`text-[11px] font-semibold uppercase tracking-[0.22em] ${themeClass.accentText}`}>Appearance</div>
                <h3 className={`mt-2 text-xl font-semibold ${themeClass.title}`}>화면 설정</h3>
              </div>
              <button
                type="button"
                className={`inline-flex h-10 w-10 items-center justify-center rounded-xl border ${themeClass.ghostButton}`}
                onClick={() => setSettingsOpen(false)}
              >
                ✕
              </button>
            </div>

            <div className="mt-5 grid gap-3 sm:grid-cols-2">
              <button
                type="button"
                className={`rounded-2xl border px-4 py-4 text-left ${theme === 'dark' ? themeClass.themeCardActive : themeClass.themeCardIdle}`}
                onClick={() => setTheme('dark')}
              >
                <div className="text-sm font-semibold">다크</div>
                <div className={`mt-1 text-xs ${themeClass.sub}`}>기존 TechNews 기본 톤</div>
              </button>
              <button
                type="button"
                className={`rounded-2xl border px-4 py-4 text-left ${theme === 'light' ? themeClass.themeCardActive : themeClass.themeCardIdle}`}
                onClick={() => setTheme('light')}
              >
                <div className="text-sm font-semibold">라이트</div>
                <div className={`mt-1 text-xs ${themeClass.sub}`}>밝은 배경과 로즈 포인트</div>
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
