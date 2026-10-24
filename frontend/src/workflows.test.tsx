import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { Login } from './App';
import { ProposalConfirmation, Support } from './customer';
import { api, post } from './api';
import type { Conversation, Proposal, Session } from './types';

vi.mock('./api', async importOriginal => {
  const actual = await importOriginal<typeof import('./api')>();
  return { ...actual, api: vi.fn(), post: vi.fn() };
});
beforeEach(() => {
  vi.mocked(api).mockReset(); vi.mocked(post).mockReset();
  HTMLDialogElement.prototype.showModal = function () { this.setAttribute('open', ''); };
  HTMLDialogElement.prototype.close = function () { this.removeAttribute('open'); };
  Element.prototype.scrollIntoView = vi.fn();
});
afterEach(cleanup);
const session: Session = { csrf_token: 'test-token', user: { id: 'staff-1', name: 'Demo Support', email: 'support@demo.local', role: 'support', available: true, teams: ['general'] } };
const proposal: Proposal = { id: 'proposal-1', kind: 'cancel_order', order_id: 'order-1', order_number: 'NS-1001', status: 'pending', reason: '', summary: 'Cancel order NS-1001 containing one item.', expires_at: '2099-01-01T12:00:00Z' };
const conversation: Conversation = { id: 'conversation-1', title: 'Order question', mode: 'assistant', updated_at: '2026-10-24T08:00:00Z', preview: '', messages: [], proposals: [], ticket: null };
describe('demo login', () => {
  it('opens only the explicitly selected account after server authentication', async () => {
    const onLogin = vi.fn(); vi.mocked(post).mockResolvedValue(session);
    render(<Login system={null} onLogin={onLogin} />);
    fireEvent.click(screen.getByRole('button', { name: /Support Care for customers/i }));
    expect(post).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: /Enter workspace/i }));
    await waitFor(() => expect(onLogin).toHaveBeenCalledWith(session));
    expect(post).toHaveBeenCalledWith('/auth/login', { email: 'support@demo.local', password: 'DemoPass123!' });
  });
  it('keeps the login form open when credentials are rejected', async () => {
    const onLogin = vi.fn(); vi.mocked(post).mockRejectedValue(new Error('Incorrect email or password.'));
    render(<Login system={null} onLogin={onLogin} />);
    fireEvent.click(screen.getByRole('button', { name: /Enter workspace/i }));
    expect(await screen.findByRole('alert')).toHaveProperty('textContent', 'Incorrect email or password.');
    expect(onLogin).not.toHaveBeenCalled();
  });
});
describe('material order changes', () => {
  it('requires an explicit confirmation and makes backing out safe', () => {
    const confirm = vi.fn(); const close = vi.fn();
    render(<ProposalConfirmation proposal={proposal} busy={false} error="" onConfirm={confirm} onClose={close} />);
    expect(confirm).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: 'Go back' }));
    expect(close).toHaveBeenCalledTimes(1); expect(confirm).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: 'Confirm cancellation' }));
    expect(confirm).toHaveBeenCalledTimes(1);
  });
  it('prevents repeated confirmation while a request is pending', () => {
    const confirm = vi.fn();
    render(<ProposalConfirmation proposal={proposal} busy error="" onConfirm={confirm} onClose={vi.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: 'Confirming…' }));
    expect(confirm).not.toHaveBeenCalled();
  });
});
describe('support conversation reliability', () => {
  it('reuses the same message ID when retrying a failed send', async () => {
    vi.mocked(api).mockImplementation(async path => path === '/conversations' ? [] : conversation);
    let attempts = 0;
    vi.mocked(post).mockImplementation(async path => {
      if (path === '/conversations') return conversation;
      attempts++;
      if (attempts === 1) throw new Error('Connection interrupted. Try again.');
      return { ...conversation, messages: [{ id: 'message-1', role: 'user', content: 'Where is my order?', mode: 'system', created_at: conversation.updated_at, citations: [] }] };
    });
    render(<Support initialMessage={null} consumeInitial={vi.fn()} />);
    fireEvent.change(screen.getByRole('textbox', { name: 'Message' }), { target: { value: 'Where is my order?' } });
    fireEvent.click(screen.getByRole('button', { name: 'Send message' }));
    await screen.findByText('Connection interrupted. Try again.');
    fireEvent.click(screen.getByRole('button', { name: 'Send message' }));
    await waitFor(() => expect(attempts).toBe(2));
    const sends = vi.mocked(post).mock.calls.filter(([path]) => path.endsWith('/messages'));
    expect(sends[0][1]).toEqual(sends[1][1]);
    expect((sends[0][1] as { client_message_id: string }).client_message_id).toMatch(/^[0-9a-f-]{36}$/);
  });
  it('labels human ownership and keeps customer messages available for staff', async () => {
    const humanConversation = { ...conversation, mode: 'human_owned', ticket: { team: 'logistics', assignee_name: 'Sam' } };
    vi.mocked(api).mockImplementation(async path => path === '/conversations' ? [humanConversation] : humanConversation);
    render(<Support initialMessage={null} consumeInitial={vi.fn()} />);
    fireEvent.click(await screen.findByRole('button', { name: /Order question/ }));
    expect(await screen.findByText(/automatic replies are paused/)).toBeTruthy();
    expect(screen.getByText('Connected with Sam')).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Talk to a person' })).toBeNull();
    expect(screen.getByRole('textbox', { name: 'Message' }).getAttribute('placeholder')).toBe('Write to the support team…');
  });
  it('prevents new messages in a closed conversation and points to a new one', async () => {
    const closed = { ...conversation, mode: 'closed' };
    vi.mocked(api).mockImplementation(async path => path === '/conversations' ? [closed] : closed);
    render(<Support initialMessage={null} consumeInitial={vi.fn()} />);
    fireEvent.click(await screen.findByRole('button', { name: /Order question/ }));
    await screen.findByText('Conversation closed');
    expect(screen.getByRole('textbox', { name: 'Message' }).hasAttribute('disabled')).toBe(true);
    expect(screen.getByRole('button', { name: 'Send message' }).hasAttribute('disabled')).toBe(true);
    expect(screen.queryByRole('button', { name: 'Talk to a person' })).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'New conversation' }));
    expect(screen.getByRole('textbox', { name: 'Message' }).hasAttribute('disabled')).toBe(false);
  });
});
