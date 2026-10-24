import { afterEach, describe, expect, it, vi } from 'vitest';
import { api, ApiError, notifySessionChange, post, SESSION_CHANGE_KEY, setSession } from './api';
import type { Session } from './types';

afterEach(() => { vi.unstubAllGlobals(); setSession(null); });
describe('session API transport', () => {
  it('keeps authentication in cookies and adds CSRF to authenticated writes', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ ok: true }), { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);
    setSession({ csrf_token: 'csrf-test' } as Session);
    await post('/orders/example', { action: 'cancel' });
    expect(fetchMock).toHaveBeenCalledWith('/api/orders/example', expect.objectContaining({ credentials: 'same-origin', method: 'POST', headers: expect.objectContaining({ 'X-CSRF-Token': 'csrf-test' }), body: '{"action":"cancel"}' }));
  });
  it('reports a rejected server action without turning it into a success', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: 'This order has already shipped.' }), { status: 409 })));
    await expect(post('/action-proposals/example/confirm')).rejects.toThrow('This order has already shipped.');
  });
  it('handles backend outages with actionable feedback', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')));
    await expect(api('/products')).rejects.toBeInstanceOf(ApiError);
    await expect(api('/products')).rejects.toThrow('Check that the backend is running');
  });
  it('clears expired sessions after an authenticated request', async () => {
    const listener = vi.fn();
    window.addEventListener('session-expired', listener);
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: 'Session expired' }), { status: 401 })));
    await expect(api('/orders')).rejects.toThrow('Session expired');
    expect(listener).toHaveBeenCalledTimes(1);
    window.removeEventListener('session-expired', listener);
  });
  it('aborts an old request and ignores its delayed 401 after a different account signs in', async () => {
    let finish!: (response: Response) => void;
    const fetchMock = vi.fn((_input: RequestInfo | URL, _init?: RequestInit) => new Promise<Response>(resolve => { finish = resolve; }));
    vi.stubGlobal('fetch', fetchMock);
    const expired = vi.fn();
    window.addEventListener('session-expired', expired);
    try {
      setSession({ csrf_token: 'old-customer-csrf' } as Session);
      const pending = api('/conversations/old-customer-thread').catch(error => error);
      const requestSignal = fetchMock.mock.calls[0][1]?.signal as AbortSignal;
      expect(requestSignal.aborted).toBe(false);
      setSession({ csrf_token: 'new-staff-csrf' } as Session);
      expect(requestSignal.aborted).toBe(true);
      // A request may already be on the server when cancellation occurs.
      finish(new Response(JSON.stringify({ detail: 'Old session expired' }), { status: 401 }));
      expect(await pending).toMatchObject({ name: 'AbortError' });
      expect(expired).not.toHaveBeenCalled();
    } finally {
      window.removeEventListener('session-expired', expired);
    }
  });
  it('does not publish an old response body after the session is cleared', async () => {
    let finishBody!: (body: unknown) => void;
    const json = vi.fn(() => new Promise(resolve => { finishBody = resolve; }));
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, status: 200, json }));
    setSession({ csrf_token: 'customer-csrf' } as Session);
    const pending = api('/orders').catch(error => error);
    await vi.waitFor(() => expect(json).toHaveBeenCalledOnce());
    setSession(null);
    finishBody([{ id: 'private-old-order' }]);
    expect(await pending).toMatchObject({ name: 'AbortError' });
  });
  it('announces account changes without writing credentials to browser storage', () => {
    window.localStorage.clear();
    setSession({ csrf_token: 'private-csrf-value' } as Session);
    notifySessionChange();
    const first = window.localStorage.getItem(SESSION_CHANGE_KEY);
    expect(first).toBeTruthy();
    expect(first).not.toContain('private-csrf-value');
    notifySessionChange();
    expect(window.localStorage.getItem(SESSION_CHANGE_KEY)).not.toBe(first);
    expect(window.localStorage.length).toBe(1);
    window.localStorage.clear();
  });
});
