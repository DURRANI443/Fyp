import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { Support } from './customer';
import { api, ApiError } from './api';
import type { Conversation } from './types';

vi.mock('./api', async importOriginal => {
  const actual = await importOriginal<typeof import('./api')>();
  return { ...actual, api: vi.fn() };
});

const conversation: Conversation = {
  id: 'customer-conversation', title: 'An order question', mode: 'handoff_pending',
  updated_at: '2026-10-24T12:00:00Z', preview: '', messages: [], proposals: [], ticket: null,
};

beforeEach(() => {
  vi.mocked(api).mockReset();
  vi.useFakeTimers();
  Element.prototype.scrollIntoView = vi.fn();
});
afterEach(() => { cleanup(); vi.useRealTimers(); });

async function openConversation() {
  let view!: ReturnType<typeof render>;
  await act(async () => { view = render(<Support initialMessage={null} consumeInitial={vi.fn()} />); });
  await act(async () => { fireEvent.click(screen.getByRole('button', { name: /An order question/ })); });
  expect(screen.getByText(/automatic replies are paused/)).toBeTruthy();
  return view;
}

describe('customer conversation polling', () => {
  it.each([401, 403, 404])('stops polling after a terminal HTTP %i response', async status => {
    let detailRequests = 0;
    vi.mocked(api).mockImplementation(async path => {
      if (path === '/conversations') return [conversation];
      detailRequests++;
      if (detailRequests === 1) return conversation;
      throw new ApiError('This conversation is no longer accessible.', status);
    });
    await openConversation();
    expect(detailRequests).toBe(1);
    await act(async () => { await vi.advanceTimersByTimeAsync(4000); });
    expect(detailRequests).toBe(2);
    expect(screen.getByRole('alert').textContent).toContain('no longer accessible');
    await act(async () => { await vi.advanceTimersByTimeAsync(16000); });
    expect(detailRequests).toBe(2);
  });

  it('prevents overlapping polls and cancels an in-flight poll when the customer workspace unmounts', async () => {
    let detailRequests = 0;
    let finish!: (value: Conversation) => void;
    let pollSignal: AbortSignal | undefined;
    vi.mocked(api).mockImplementation(async (path, options) => {
      if (path === '/conversations') return [conversation];
      detailRequests++;
      if (detailRequests === 1) return conversation;
      pollSignal = options?.signal;
      return new Promise<Conversation>(resolve => { finish = resolve; });
    });
    const view = await openConversation();
    await act(async () => { await vi.advanceTimersByTimeAsync(4000); });
    expect(detailRequests).toBe(2);
    expect(pollSignal?.aborted).toBe(false);
    await act(async () => { await vi.advanceTimersByTimeAsync(12000); });
    expect(detailRequests).toBe(2);
    view.unmount();
    expect(pollSignal?.aborted).toBe(true);
    await act(async () => { finish(conversation); await vi.advanceTimersByTimeAsync(12000); });
    expect(detailRequests).toBe(2);
    expect(screen.queryByRole('textbox', { name: 'Message' })).toBeNull();
  });
});
