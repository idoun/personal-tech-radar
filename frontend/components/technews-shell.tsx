'use client';

import { useEffect, useMemo, useState } from 'react';

import { fetchIssue, fetchIssueGroups, fetchLatestIssue } from '@/lib/api';
import type { IssueDetail, IssueGroupMonth } from '@/lib/types';

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

type ArticleCard = {
  title: string;
  summary: string;
  source?: string;
  geeknews?: string;
  ai: boolean;
};

function buildTopSummary(detail: IssueDetail, _cards: ArticleCard[]) {
  return buildFallbackSummary(detail.summary);
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
    } else if (line.startsWith('- 원문:')) {
      current.source = line.replace('- 원문:', '').trim();
    } else if (line.startsWith('- GeekNews:')) {
      current.geeknews = line.replace('- GeekNews:', '').trim();
    }
  }

  if (current) cards.push(current);
  return { intro, cards };
}

export function TechNewsShell() {
  const [groups, setGroups] = useState<IssueGroupMonth[]>([]);
  const [active, setActive] = useState<IssueDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const [groupData, latest] = await Promise.all([fetchIssueGroups(), fetchLatestIssue()]);
        setGroups(groupData);
        setActive(latest);
        const initial: Record<string, boolean> = {};
        const latestKey = groupData[0] ? `${groupData[0].year}-${groupData[0].month}` : null;
        for (const group of groupData) {
          const key = `${group.year}-${group.month}`;
          initial[key] = key === latestKey;
        }
        setExpanded(initial);
      } catch (err) {
        setError(err instanceof Error ? err.message : '불러오지 못했습니다.');
      } finally {
        setLoading(false);
      }
    }

    void load();
  }, []);

  async function handleOpen(slug: string) {
    try {
      const issue = await fetchIssue(slug);
      setActive(issue);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : '문서를 열지 못했습니다.');
    }
  }

  const parsed = active ? parseIssueBody(active.markdown) : { intro: [], cards: [] };
  const topSummary = active ? buildTopSummary(active, parsed.cards) : '';
  const grouped = useMemo(
    () =>
      groups.map((group) => ({
        ...group,
        items: group.items.map((item) => ({
          ...item,
          derivedSummary: active?.slug === item.slug ? topSummary : buildFallbackSummary(item.summary),
        })),
      })),
    [groups, active, topSummary],
  );

  return (
    <div className="flex h-screen overflow-hidden bg-slate-950 text-slate-100">
      {mobileSidebarOpen ? (
        <button
          type="button"
          aria-label="목록 닫기"
          className="fixed inset-0 z-30 bg-slate-950/70 md:hidden"
          onClick={() => setMobileSidebarOpen(false)}
        />
      ) : null}

      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-[320px] shrink-0 flex-col border-r border-slate-800 bg-slate-950/95 transition-transform md:static md:translate-x-0 ${
          mobileSidebarOpen ? 'translate-x-0' : '-translate-x-full'
        } md:flex`}
      >
        <div className="border-b border-slate-800 px-5 py-4">
          <div className="text-xs uppercase tracking-[0.24em] text-sky-300">TechNews</div>
          <h1 className="mt-2 text-xl font-semibold">GeekNews Archive</h1>
          <p className="mt-2 text-sm text-slate-400">텔레그램으로 보내는 요약을 날짜별로 모아보는 공간</p>
        </div>
        <div className="flex-1 overflow-y-auto px-3 py-3">
          {grouped.map((group) => {
            const key = `${group.year}-${group.month}`;
            const isExpanded = expanded[key] ?? false;
            return (
              <div key={key} className="mb-3 rounded-2xl border border-slate-800 bg-slate-900/60">
                <button
                  type="button"
                  onClick={() => setExpanded((prev) => ({ ...prev, [key]: !isExpanded }))}
                  className="flex w-full items-center justify-between px-4 py-3 text-left"
                >
                  <span className="text-sm font-medium text-slate-200">{monthLabel(group.year, group.month)}</span>
                  <span className="text-xs text-slate-400">{isExpanded ? '접기' : '펼치기'}</span>
                </button>
                {isExpanded ? (
                  <div className="border-t border-slate-800 px-2 py-2">
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
                          className={`mb-1 w-full rounded-xl px-3 py-3 text-left transition ${
                            activeSlug ? 'bg-sky-500/15 text-sky-100' : 'hover:bg-slate-800/70 text-slate-300'
                          }`}
                        >
                          <div className="text-xs text-slate-400">{formatLongDate(item.issue_date)}</div>
                          <div className="mt-1 line-clamp-2 text-sm font-medium">{item.title}</div>
                          <div className="mt-1 line-clamp-2 text-xs text-slate-400">{item.derivedSummary}</div>
                        </button>
                      );
                    })}
                  </div>
                ) : null}
              </div>
            );
          })}
        </div>
      </aside>

      <main className="flex min-w-0 flex-1 flex-col overflow-y-auto">
        <div className="border-b border-slate-800 bg-slate-950/90 px-4 py-4 md:px-8">
          <div className="flex items-center justify-between gap-3">
            <div className="text-xs uppercase tracking-[0.24em] text-sky-300">Published brief</div>
            <button
              type="button"
              className="inline-flex items-center rounded-full border border-slate-700 bg-slate-900/80 px-3 py-1 text-xs text-slate-200 md:hidden"
              onClick={() => setMobileSidebarOpen(true)}
            >
              목록 보기
            </button>
          </div>
          <h2 className="mt-2 text-2xl font-semibold">{active?.title ?? 'GeekNews Daily Summary'}</h2>
          <p className="mt-2 text-sm text-slate-400">{active ? formatLongDate(active.issue_date) : '문서를 고르는 중'}</p>
        </div>

        <div className="mx-auto w-full max-w-5xl flex-1 px-4 py-6 md:px-8 md:py-8">
          {loading ? <div className="text-slate-400">불러오는 중...</div> : null}
          {error ? <div className="rounded-2xl border border-rose-900 bg-rose-950/40 px-4 py-3 text-sm text-rose-200">{error}</div> : null}
          {!loading && active ? (
            <article className="rounded-3xl border border-slate-800 bg-slate-900/70 p-6 shadow-2xl shadow-slate-950/40 md:p-8">
              <div className="rounded-2xl border border-sky-500/20 bg-sky-500/10 px-4 py-3 md:px-5">
                <div className="text-[11px] font-semibold uppercase tracking-[0.2em] text-sky-300">핵심 한줄</div>
                <div className="mt-2 max-w-3xl text-sm font-medium leading-6 text-slate-100 md:text-base md:leading-7">{topSummary}</div>
              </div>

              {parsed.intro.length > 0 ? (
                <div className="mt-6 space-y-3 rounded-2xl border border-slate-800 bg-slate-950/40 px-5 py-4 text-[15px] leading-7 text-slate-300">
                  {parsed.intro.map((line, index) => (
                    <p key={`${line}-${index}`}>{line}</p>
                  ))}
                </div>
              ) : null}

              <div className="mt-6 space-y-4">
                {parsed.cards.map((card, index) => (
                  <section key={`${card.title}-${index}`} className="rounded-2xl border border-slate-800 bg-slate-950/50 p-5">
                    <h3 className="text-xl font-semibold leading-8 text-slate-50">
                      {card.ai ? <span className="mr-2">🤖</span> : null}
                      <span className={card.ai ? 'font-bold' : ''}>{card.title}</span>
                    </h3>
                    <p className="mt-3 text-[15px] leading-7 text-slate-300">{card.summary}</p>
                    <div className="mt-4 flex flex-wrap gap-2">
                      {card.source ? (
                        <a
                          href={card.source}
                          target="_blank"
                          rel="noreferrer"
                          className="rounded-full border border-sky-500/30 bg-sky-500/10 px-3 py-1 text-sm text-sky-200 transition hover:bg-sky-500/20"
                        >
                          원문 보기
                        </a>
                      ) : null}
                      {card.geeknews ? (
                        <a
                          href={card.geeknews}
                          target="_blank"
                          rel="noreferrer"
                          className="rounded-full border border-slate-700 bg-slate-800/80 px-3 py-1 text-sm text-slate-200 transition hover:bg-slate-700"
                        >
                          GeekNews 글 보기
                        </a>
                      ) : null}
                    </div>
                  </section>
                ))}
              </div>
            </article>
          ) : null}
        </div>
      </main>
    </div>
  );
}
