import type { IssueDetail, IssueGroupMonth } from './types';

function getApiBaseUrl() {
  if (process.env.NEXT_PUBLIC_API_BASE_URL) {
    return process.env.NEXT_PUBLIC_API_BASE_URL;
  }

  if (typeof window !== 'undefined') {
    return `${window.location.protocol}//${window.location.host}/technews-api`;
  }

  return 'http://127.0.0.1:8010';
}

async function apiFetch<T>(path: string): Promise<T> {
  const response = await fetch(`${getApiBaseUrl()}${path}`, { cache: 'no-store' });
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function fetchIssueGroups() {
  return apiFetch<IssueGroupMonth[]>('/api/issues');
}

export function fetchLatestIssue() {
  return apiFetch<IssueDetail>('/api/issues/latest');
}

export function fetchIssue(slug: string) {
  return apiFetch<IssueDetail>(`/api/issues/${slug}`);
}
