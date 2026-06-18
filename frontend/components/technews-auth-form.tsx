'use client';

import { useState } from 'react';

import { getFriendlyErrorMessage } from '@/lib/api';

type Props = {
  onSubmit: (email: string, password: string) => Promise<void>;
};

export function TechNewsAuthForm({ onSubmit }: Props) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError('');
    try {
      await onSubmit(email, password);
    } catch (err) {
      setError(getFriendlyErrorMessage(err, '로그인하지 못했습니다.'));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-950 px-4 text-slate-100">
      <form onSubmit={handleSubmit} className="w-full max-w-md rounded-[2rem] border border-slate-800 bg-slate-900/90 p-8 shadow-2xl shadow-black/30">
        <p className="mb-3 text-sm uppercase tracking-[0.3em] text-sky-300">Shared Sign-In</p>
        <h1 className="text-3xl font-semibold text-white">Personal Tech Radar</h1>

        <label className="mt-8 block text-sm text-slate-300">이메일</label>
        <input
          type="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          className="mt-2 w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100 outline-none"
          required
        />

        <label className="mt-4 block text-sm text-slate-300">비밀번호</label>
        <input
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          className="mt-2 w-full rounded-2xl border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100 outline-none"
          required
        />

        {error ? <div className="mt-4 rounded-2xl border border-rose-900 bg-rose-950/40 px-4 py-3 text-sm text-rose-200">{error}</div> : null}

        <button
          type="submit"
          disabled={loading}
          className="mt-6 w-full rounded-2xl bg-sky-500 px-4 py-3 font-medium text-slate-950 transition hover:bg-sky-400 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {loading ? '로그인 중...' : '로그인'}
        </button>

        <a
          href="/"
          className="mt-4 block text-center text-sm text-slate-400 underline underline-offset-4 hover:text-slate-200"
        >
          채팅 앱으로 이동
        </a>
      </form>
    </div>
  );
}
