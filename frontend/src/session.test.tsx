import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import App from './App';
import { api, post, SESSION_CHANGE_KEY, setSession } from './api';
import type { Session, System } from './types';

vi.mock('./api', async importOriginal => {
  const actual = await importOriginal<typeof import('./api')>();
  return { ...actual, api: vi.fn(), post: vi.fn() };
});

const customer: Session = {
  csrf_token: 'customer-session-csrf',
  user: { id: 'customer-1', name: 'Alex Morgan', email: 'customer@demo.local', role: 'customer', teams: [], available: true },
};
const system: System = {
  version: '0.2.1', llm_mode: 'offline', llm_configured: false,
  model: null, knowledge_mode: 'tfidf_fallback', notice: 'Synthetic demo',
};

beforeEach(() => {
  vi.mocked(api).mockReset();
  vi.mocked(post).mockReset();
  setSession(null);
  window.localStorage.clear();
});
afterEach(() => { cleanup(); setSession(null); });

function changedInAnotherTab(key = SESSION_CHANGE_KEY) {
  fireEvent(window, new StorageEvent('storage', { key, newValue: 'other-tab-change', storageArea: window.localStorage }));
}

describe('shared-browser account changes', () => {
  it('clears an already mounted customer workspace when another tab changes the session', async () => {
    vi.mocked(api).mockImplementation(async path => {
      if (path === '/auth/me') return customer;
      if (path === '/system') return system;
      return [];
    });
    render(<App />);
    expect(await screen.findByRole('navigation', { name: 'Main navigation' })).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Get support' })).toBeTruthy();
    changedInAnotherTab('unrelated-preference');
    expect(screen.getByRole('navigation', { name: 'Main navigation' })).toBeTruthy();
    changedInAnotherTab();
    expect(await screen.findByRole('button', { name: 'Enter workspace' })).toBeTruthy();
    expect(screen.queryByRole('navigation', { name: 'Main navigation' })).toBeNull();
    expect(screen.queryByRole('button', { name: 'Get support' })).toBeNull();
    expect(screen.getByText(/another tab/i)).toBeTruthy();
  });

  it('does not restore a previous account when bootstrap finishes after a remote session change', async () => {
    let finishAuth!: (session: Session) => void;
    const pendingAuth = new Promise<Session>(resolve => { finishAuth = resolve; });
    vi.mocked(api).mockImplementation(async path => {
      if (path === '/auth/me') return pendingAuth;
      if (path === '/system') return system;
      return [];
    });
    render(<App />);
    changedInAnotherTab();
    expect(await screen.findByRole('button', { name: 'Enter workspace' })).toBeTruthy();
    await act(async () => { finishAuth(customer); await pendingAuth; });
    expect(screen.getByRole('button', { name: 'Enter workspace' })).toBeTruthy();
    expect(screen.queryByRole('navigation', { name: 'Main navigation' })).toBeNull();
    expect(screen.queryByText('Alex Morgan')).toBeNull();
  });
});
