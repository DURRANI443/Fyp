import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { Orders, Support } from './customer';
import { Inbox, Team } from './staff';
import { api, patch, post } from './api';
import type { Conversation, Order, Ticket, User } from './types';

vi.mock('./api', async importOriginal => {
  const actual = await importOriginal<typeof import('./api')>();
  return { ...actual, api: vi.fn(), patch: vi.fn(), post: vi.fn() };
});

const first: Conversation = { id: 'first', title: 'First customer question', mode: 'assistant', updated_at: '2026-10-24T12:00:00Z', preview: '', messages: [], proposals: [], ticket: null };
const second: Conversation = { ...first, id: 'second', title: 'Second customer question' };
const user: User = { id: 'staff', name: 'Sam', email: 'support@demo.local', role: 'support', available: true, teams: ['general', 'billing'] };
const ticket: Ticket = { id: 'ticket-first', conversation_id: first.id, customer_name: 'Alex', subject: 'A delivery question', team: 'general', priority: 'normal', status: 'assigned', assignee_id: user.id, assignee_name: user.name, summary: 'A customer needs help.', routing_reason: 'General support request', created_at: first.updated_at, updated_at: first.updated_at };

beforeEach(() => {
  vi.mocked(api).mockReset();
  vi.mocked(patch).mockReset();
  vi.mocked(post).mockReset();
  Element.prototype.scrollIntoView = vi.fn();
  HTMLDialogElement.prototype.showModal = function () { this.setAttribute('open', ''); };
  HTMLDialogElement.prototype.close = function () { this.removeAttribute('open'); };
});
afterEach(cleanup);

describe('customer navigation while history is loading', () => {
  it('can start a new conversation while an existing conversation request is still pending', async () => {
    vi.mocked(api).mockImplementation(async path => path === '/conversations' ? [first] : new Promise(() => {}));
    render(<Support initialMessage={null} consumeInitial={vi.fn()} />);
    fireEvent.click(await screen.findByRole('button', { name: /First customer question/ }));
    await screen.findByText('Opening conversation…');
    fireEvent.click(screen.getByRole('button', { name: 'New conversation' }));
    await waitFor(() => expect(screen.getByRole('textbox', { name: 'Message' }).hasAttribute('disabled')).toBe(false));
    expect(screen.queryByText('Opening conversation…')).toBeNull();
  });

  it('can return to the loaded conversation while a different history request is pending', async () => {
    vi.mocked(api).mockImplementation(async path => {
      if (path === '/conversations') return [first, second];
      if (path === '/conversations/first') return first;
      return new Promise(() => {});
    });
    render(<Support initialMessage={null} consumeInitial={vi.fn()} />);
    fireEvent.click(await screen.findByRole('button', { name: /First customer question/ }));
    await waitFor(() => expect(screen.getByRole('textbox', { name: 'Message' }).hasAttribute('disabled')).toBe(false));
    fireEvent.click(screen.getByRole('button', { name: /Second customer question/ }));
    await screen.findByText('Opening conversation…');
    fireEvent.click(screen.getByRole('button', { name: /First customer question/ }));
    await waitFor(() => expect(screen.getByRole('textbox', { name: 'Message' }).hasAttribute('disabled')).toBe(false));
    expect(screen.queryByText('Opening conversation…')).toBeNull();
  });

  it('blocks sending to unavailable history and lets the customer retry loading it', async () => {
    let attempts = 0;
    vi.mocked(api).mockImplementation(async path => {
      if (path === '/conversations') return [first];
      if (++attempts === 1) throw new Error('Connection interrupted.');
      return first;
    });
    render(<Support initialMessage={null} consumeInitial={vi.fn()} />);
    fireEvent.click(await screen.findByRole('button', { name: /First customer question/ }));
    await screen.findByText('Connection interrupted.');
    expect(screen.getByRole('textbox', { name: 'Message' }).hasAttribute('disabled')).toBe(true);
    expect(screen.getByRole('textbox', { name: 'Message' }).getAttribute('maxLength')).toBe('3000');
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }));
    await waitFor(() => expect(screen.getByRole('textbox', { name: 'Message' }).hasAttribute('disabled')).toBe(false));
    expect(attempts).toBe(2);
    expect(post).not.toHaveBeenCalled();
  });
});

describe('return form availability', () => {
  it('offers only items with remaining quantity and keeps input within API limits', async () => {
    const item = { id: 'reserved-item', product_id: 'p1', name: 'Already requested shirt', quantity: 1, returnable_quantity: 0, price_cents: 2000, color: 'sage', icon: 'shirt' };
    const order: Order = {
      id: 'delivered-order', number: 'NS-1024', customer_id: 'customer', status: 'delivered', shipping_status: 'Delivered', tracking_number: null,
      created_at: first.updated_at, delivered_at: first.updated_at, total_cents: 6000, currency: 'USD', version: 1,
      items: [item, { ...item, id: 'remaining-item', name: 'Returnable cap', quantity: 3, returnable_quantity: 2 }],
      returns: [{ id: 'return-1', item_id: item.id, quantity: 1, status: 'requested', reason: 'Wrong size' }],
      timeline: [], can_cancel: false, can_return: true,
    };
    vi.mocked(api).mockResolvedValue([order]);
    render(<Orders ask={vi.fn()} />);
    fireEvent.click(await screen.findByRole('button', { name: 'Start a return' }));
    const items = screen.getByRole('combobox', { name: 'Item' });
    expect(within(items).queryByRole('option', { name: 'Already requested shirt' })).toBeNull();
    expect((items as HTMLSelectElement).value).toBe('remaining-item');
    expect(screen.getByRole('spinbutton', { name: 'Quantity' }).getAttribute('max')).toBe('2');
    expect(screen.getByRole('textbox', { name: 'Reason for return' }).getAttribute('maxLength')).toBe('500');
  });
});

describe('admin team refresh', () => {
  it('reflects changed server membership when another member save reloads the team list', async () => {
    const admin: User = { ...user, id: 'admin', role: 'admin', name: 'Admin' };
    let members = [user, admin];
    vi.mocked(api).mockImplementation(async () => members);
    vi.mocked(patch).mockImplementation(async () => {
      members = [{ ...user, available: false, teams: ['billing'] }, { ...admin, available: false }];
      return members[1];
    });
    render(<Team />);
    const adminCard = (await screen.findByRole('heading', { name: 'Admin' })).closest('article')!;
    const staffCard = screen.getByText('Sam').closest('article')!;
    fireEvent.click(within(adminCard).getByRole('checkbox', { name: /Available for support/ }));
    fireEvent.click(within(adminCard).getByRole('button', { name: 'Save changes' }));
    await waitFor(() => expect((within(staffCard).getByRole('checkbox', { name: /Available for support/ }) as HTMLInputElement).checked).toBe(false));
    expect((within(staffCard).getByRole('checkbox', { name: 'General' }) as HTMLInputElement).checked).toBe(false);
    expect((within(staffCard).getByRole('checkbox', { name: 'Billing' }) as HTMLInputElement).checked).toBe(true);
  });
});

describe('staff filtered selection', () => {
  it('shows a ticket history load failure and allows a retry', async () => {
    let attempts = 0;
    vi.mocked(api).mockImplementation(async path => {
      if (path === '/staff/tickets') return [ticket];
      if (++attempts === 1) throw new Error('Ticket history is temporarily unavailable.');
      return { ticket, conversation: first };
    });
    render(<Inbox user={user} />);
    await screen.findByText('Ticket history is temporarily unavailable.');
    expect(screen.queryByLabelText('Reply to Alex')).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }));
    await screen.findByLabelText('Reply to Alex');
    expect(attempts).toBe(2);
  });

  it('keeps the selected ticket stable while a reply is being submitted', async () => {
    let finishReply!: (value: unknown) => void;
    vi.mocked(api).mockImplementation(async path => path === '/staff/tickets' ? [ticket] : { ticket, conversation: first });
    vi.mocked(post).mockImplementation(() => new Promise(resolve => { finishReply = resolve; }));
    render(<Inbox user={user} />);
    fireEvent.change(await screen.findByLabelText('Reply to Alex'), { target: { value: 'Your parcel is on its way.' } });
    fireEvent.click(screen.getByRole('button', { name: /Send reply/ }));
    expect(screen.getByRole('textbox', { name: 'Search tickets' }).hasAttribute('disabled')).toBe(true);
    expect(screen.getByRole('combobox', { name: 'Filter team' }).hasAttribute('disabled')).toBe(true);
    expect(screen.getByRole('combobox', { name: 'Filter status' }).hasAttribute('disabled')).toBe(true);
    finishReply({});
    await waitFor(() => expect(screen.getByRole('textbox', { name: 'Search tickets' }).hasAttribute('disabled')).toBe(false));
  });

  it('removes the selected ticket and reply form when search excludes every ticket', async () => {
    vi.mocked(api).mockImplementation(async path => path === '/staff/tickets' ? [ticket] : { ticket, conversation: first });
    render(<Inbox user={user} />);
    await screen.findByLabelText('Reply to Alex');
    fireEvent.click(screen.getByRole('button', { name: /A delivery question/ }));
    fireEvent.change(screen.getByRole('textbox', { name: 'Search tickets' }), { target: { value: 'no-such-customer' } });
    await screen.findByText('All clear here');
    await waitFor(() => expect(screen.queryByLabelText('Reply to Alex')).toBeNull());
  });

  it('clears a pending ticket loader when a team filter has no matches', async () => {
    vi.mocked(api).mockImplementation(async path => path === '/staff/tickets' ? [ticket] : new Promise(() => {}));
    render(<Inbox user={user} />);
    await screen.findByText('Opening ticket…');
    fireEvent.change(screen.getByRole('combobox', { name: 'Filter team' }), { target: { value: 'billing' } });
    await screen.findByText('All clear here');
    await waitFor(() => expect(screen.queryByText('Opening ticket…')).toBeNull());
    expect(screen.getByText('A clear view of every conversation')).toBeTruthy();
  });
});

describe('admin ticket intervention', () => {
  it('lets an admin reply, review a return, and resolve another member’s assigned ticket', async () => {
    const admin: User = { ...user, id: 'admin', name: 'Admin', role: 'admin' };
    const order: Order = {
      id: 'delivered-order', number: 'NS-1024', customer_id: 'customer', status: 'delivered', shipping_status: 'Delivered', tracking_number: null,
      created_at: first.updated_at, delivered_at: first.updated_at, total_cents: 2000, currency: 'USD', version: 1,
      items: [], returns: [{ id: 'return-1', item_id: 'item-1', quantity: 1, status: 'requested', reason: 'Wrong size' }],
      timeline: [], can_cancel: false, can_return: false,
    };
    vi.mocked(api).mockImplementation(async path => path === '/staff/tickets' ? [ticket] : { ticket, conversation: first, order });
    vi.mocked(post).mockResolvedValue({});
    render(<Inbox user={admin} />);
    const reply = await screen.findByLabelText('Reply to Alex');
    expect(screen.getByText('You are acting as an administrator on Sam’s assigned conversation.')).toBeTruthy();
    fireEvent.change(reply, { target: { value: 'I can help resolve this return.' } });
    fireEvent.click(screen.getByRole('button', { name: /Send reply/ }));
    await waitFor(() => expect(post).toHaveBeenCalledWith('/staff/tickets/ticket-first/messages', { content: 'I can help resolve this return.' }));
    await waitFor(() => expect(screen.getByRole('button', { name: 'Approve' }).hasAttribute('disabled')).toBe(false));
    fireEvent.click(screen.getByRole('button', { name: 'Approve' }));
    await waitFor(() => expect(post).toHaveBeenCalledWith('/staff/returns/return-1/review', { status: 'approved' }));
    await waitFor(() => expect(screen.getByRole('button', { name: 'Resolve conversation' }).hasAttribute('disabled')).toBe(false));
    fireEvent.click(screen.getByRole('button', { name: 'Resolve conversation' }));
    const summary = screen.getByRole('textbox', { name: 'Resolution summary' });
    expect(summary.getAttribute('maxLength')).toBe('1000');
    fireEvent.change(summary, { target: { value: 'Return approved and explained.' } });
    fireEvent.click(screen.getByRole('button', { name: 'Mark as resolved' }));
    await waitFor(() => expect(post).toHaveBeenCalledWith('/staff/tickets/ticket-first/resolve', { outcome: 'Return approved and explained.', return_to_assistant: true }));
  });

  it.each([
    { role: 'support' as const, assignee: 'another-staff', name: 'Other staff member' },
    { role: 'admin' as const, assignee: null, name: null },
  ])('requires a claim before an unassigned admin reply and keeps other support assignments read-only ($role)', async ({ role, assignee, name }) => {
    const assigned = { ...ticket, assignee_id: assignee, assignee_name: name };
    vi.mocked(api).mockImplementation(async path => path === '/staff/tickets' ? [assigned] : { ticket: assigned, conversation: first });
    render(<Inbox user={{ ...user, role }} />);
    await screen.findByRole('heading', { name: ticket.subject });
    expect(screen.queryByLabelText('Reply to Alex')).toBeNull();
    expect(screen.queryByRole('button', { name: 'Resolve conversation' })).toBeNull();
    if (!assignee) expect(await screen.findByRole('button', { name: 'Assign to me' })).toBeTruthy();
    expect(post).not.toHaveBeenCalled();
  });
});
