'use client';

import { useEffect, useMemo, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

import { fetchIssue, fetchIssueGroups, fetchLatestIssue } from '@/lib/api';
import type { IssueDetail, IssueGroupMonth } from '@/lib/types';

function formatLongDate(value: string) {
  return new Intl.DateTimeFormat('ko-KR', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    weekday: 'short',
  }).format(new Date(value));
}

function monthLabel(year: number, month: number) {
  return `${year}년 ${month}월`;
}

export function TechNewsShell() {
  const [groups, setGroups] = useState<IssueGroupMonth[]>([]);
  const [active, setActive] = useState<IssueDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  useEffect(() => {
    async function load() {
      try {
        const [groupData, latest] = await Promise.all([fetchIssueGroups(), fetchLatestIssue()]);
        setGroups(groupData);
        setActive(latest);
        const current = new Date();
        const initial: Record<string, boolean> = {};
        for (const group of groupData) {
          const key = `${group.year}-${group.month}`;
          initial[key] = group.year === current.getFullYear() && group.month === current.getMonth() + 1;
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

  const grouped = useMemo(() => groups, [groups]);

  return (
    <div className="flex min-h-screen bg-slate-950 text-slate-100">
      <aside className="hidden w-[320px] shrink-0 border-r border-slate-800 bg-slate-950/95 md:flex md:flex-col">
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
                          onClick={() => void handleOpen(item.slug)}
                          className={`mb-1 w-full rounded-xl px-3 py-3 text-left transition ${
                            activeSlug ? 'bg-sky-500/15 text-sky-100' : 'hover:bg-slate-800/70 text-slate-300'
                          }`}
                        >
                          <div className="text-xs text-slate-400">{formatLongDate(item.issue_date)}</div>
                          <div className="mt-1 line-clamp-2 text-sm font-medium">{item.title}</div>
                          <div className="mt-1 line-clamp-2 text-xs text-slate-400">{item.summary}</div>
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

      <main className="flex min-w-0 flex-1 flex-col">
        <div className="border-b border-slate-800 bg-slate-950/90 px-4 py-4 md:px-8">
          <div className="text-xs uppercase tracking-[0.24em] text-sky-300">Published brief</div>
          <h2 className="mt-2 text-2xl font-semibold">{active?.title ?? 'GeekNews Daily Summary'}</h2>
          <p className="mt-2 text-sm text-slate-400">{active ? formatLongDate(active.issue_date) : '문서를 고르는 중'}</p>
        </div>

        <div className="mx-auto w-full max-w-5xl flex-1 px-4 py-6 md:px-8 md:py-8">
          {loading ? <div className="text-slate-400">불러오는 중...</div> : null}
          {error ? <div className="rounded-2xl border border-rose-900 bg-rose-950/40 px-4 py-3 text-sm text-rose-200">{error}</div> : null}
          {!loading && active ? (
            <article className="rounded-3xl border border-slate-800 bg-slate-900/70 p-6 shadow-2xl shadow-slate-950/40 md:p-8">
              <header className="mb-8 border-b border-slate-800 pb-6">
                <div className="text-sm text-slate-400">발행일 {formatLongDate(active.issue_date)}</div>
                <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-50">{active.title}</h1>
                <p className="mt-3 max-w-3xl text-base leading-7 text-slate-300">{active.summary}</p>
              </header>
              <div className="prose-technews max-w-none text-[15px]">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{active.markdown}</ReactMarkdown>
              </div>
            </article>
          ) : null}
        </div>
      </main>
    </div>
  );
}
