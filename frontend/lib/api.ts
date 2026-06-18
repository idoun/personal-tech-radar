import type { AuthSession, IssueDetail, IssueGroupMonth } from './types';

function getSiteOrigin() {
  if (typeof window === 'undefined') {
    return 'http://127.0.0.1:3000';
  }

  if (window.location.hostname === '127.0.0.1' && window.location.port === '3012') {
    return 'http://127.0.0.1:8000';
  }

  return `${window.location.protocol}//${window.location.host}`;
}

function getApiBaseUrl() {
  if (process.env.NEXT_PUBLIC_API_BASE_URL) {
    return process.env.NEXT_PUBLIC_API_BASE_URL;
  }

  if (typeof window !== 'undefined' && window.location.hostname === '127.0.0.1' && window.location.port === '3012') {
    return 'http://127.0.0.1:8010';
  }

  if (typeof window !== 'undefined') {
    return `${window.location.protocol}//${window.location.host}/technews-api`;
  }

  return 'http://127.0.0.1:8010';
}

function getAuthBaseUrl() {
  if (process.env.NEXT_PUBLIC_AUTH_API_BASE_URL) {
    return process.env.NEXT_PUBLIC_AUTH_API_BASE_URL;
  }

  return getSiteOrigin();
}

export function getFriendlyErrorMessage(error: unknown, fallback = '요청을 처리하지 못했습니다. 잠시 후 다시 시도해주세요.') {
  if (error instanceof Error) {
    const message = error.message.trim();

    if (!message) {
      return fallback;
    }

    if ((message.startsWith('{') && message.endsWith('}')) || (message.startsWith('[') && message.endsWith(']'))) {
      try {
        const parsed = JSON.parse(message) as { detail?: string; message?: string };
        if (typeof parsed.detail === 'string' && parsed.detail.trim()) {
          return parsed.detail.trim();
        }
        if (typeof parsed.message === 'string' && parsed.message.trim()) {
          return parsed.message.trim();
        }
      } catch {
        // ignore JSON parse failure
      }
    }

    if (message === 'Failed to fetch') {
      return '서버에 연결하지 못했어요. 잠시 후 다시 시도해주세요.';
    }

    if (message.includes('401')) {
      return '로그인이 필요하거나 세션이 만료되었습니다.';
    }

    if (message.includes('403')) {
      return '접근 권한이 없습니다.';
    }

    return message;
  }

  return fallback;
}

async function requestJson<T>(url: string, options?: RequestInit): Promise<T> {
  const headers = new Headers(options?.headers || {});
  if (!headers.has('Content-Type') && options?.body) {
    headers.set('Content-Type', 'application/json');
  }

  let response: Response;
  try {
    response = await fetch(url, {
      ...options,
      headers,
      cache: 'no-store',
      credentials: 'include',
    });
  } catch (error) {
    throw new Error(getFriendlyErrorMessage(error));
  }

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `API request failed: ${response.status}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const text = await response.text();
  return text ? (JSON.parse(text) as T) : (undefined as T);
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  return requestJson<T>(`${getApiBaseUrl()}${path}`, options);
}

async function authFetch<T>(path: string, options?: RequestInit): Promise<T> {
  return requestJson<T>(`${getAuthBaseUrl()}${path}`, options);
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

export function fetchAuthSession() {
  return authFetch<AuthSession>('/api/auth/session');
}

export function loginWithPassword(email: string, password: string) {
  return authFetch<{ access_token: string; token_type: string }>('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
}

export function logoutSharedSession() {
  return authFetch<void>('/api/auth/logout', {
    method: 'POST',
  });
}
