import type { Session } from './types';

let csrfToken = '';
let sessionGeneration = 0;
const pendingRequests = new Set<AbortController>();
export const SESSION_CHANGE_KEY = 'northstar.session-change';
export class ApiError extends Error {
  constructor(message: string, public status: number) { super(message); this.name = 'ApiError'; }
}
export function setSession(session: Session | null) {
  sessionGeneration++;
  csrfToken = session?.csrf_token ?? '';
  for (const request of pendingRequests) request.abort();
  pendingRequests.clear();
}
// Cookies are shared between tabs. Broadcast only an invalidation marker,
// never a token, user record, or conversation. Initial session hydration is silent.
export function notifySessionChange() {
  try { localStorage.setItem(SESSION_CHANGE_KEY, crypto.randomUUID()); }
  catch { /* Storage may be disabled; terminal API errors still stop polling. */ }
}
export async function api<T>(path: string, options: { method?: string; body?: unknown; signal?: AbortSignal } = {}): Promise<T> {
  const method = options.method ?? 'GET';
  const generation = sessionGeneration;
  const controller = new AbortController();
  const abort = () => controller.abort();
  options.signal?.addEventListener('abort', abort, { once: true });
  if (options.signal?.aborted) controller.abort();
  pendingRequests.add(controller);
  const checkCurrent = () => {
    if (controller.signal.aborted || generation !== sessionGeneration) throw new DOMException('Request belongs to an inactive session.', 'AbortError');
  };
  try {
    checkCurrent();
    let response: Response;
    try {
      response = await fetch(`/api${path}`, {
        method, credentials: 'same-origin', signal: controller.signal,
        headers: { Accept: 'application/json', ...(options.body !== undefined ? { 'Content-Type': 'application/json' } : {}), ...(method !== 'GET' && csrfToken ? { 'X-CSRF-Token': csrfToken } : {}) },
        ...(options.body !== undefined ? { body: JSON.stringify(options.body) } : {}),
      });
    } catch (error) {
      checkCurrent();
      if (error instanceof DOMException && error.name === 'AbortError') throw error;
      throw new ApiError('The local server could not be reached. Check that the backend is running, then try again.', 0);
    }
    const data = await response.json().catch(() => null);
    checkCurrent();
    if (!response.ok) {
      if (response.status === 401 && path !== '/auth/login' && path !== '/auth/me') window.dispatchEvent(new Event('session-expired'));
      const detail = typeof data?.detail === 'string' ? data.detail : response.status === 422 ? 'Please check the information entered and try again.' : `The request could not be completed (${response.status}).`;
      throw new ApiError(detail, response.status);
    }
    return data as T;
  } finally {
    pendingRequests.delete(controller);
    options.signal?.removeEventListener('abort', abort);
  }
}
export const post = <T>(path: string, body: unknown = {}) => api<T>(path, { method: 'POST', body });
export const patch = <T>(path: string, body: unknown) => api<T>(path, { method: 'PATCH', body });
export const errorText = (error: unknown) => error instanceof Error ? error.message : 'Something went wrong. Please try again.';
