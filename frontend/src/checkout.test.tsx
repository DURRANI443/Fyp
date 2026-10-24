import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { useState } from 'react';
import { ApiError, api, post } from './api';
import { Login } from './App';
import { Cart, Shop } from './store';
import type { CartLine, CheckoutQuote, CheckoutResult, Product, System } from './types';

vi.mock('./api', async importOriginal => ({ ...await importOriginal<typeof import('./api')>(), api: vi.fn(), post: vi.fn() }));
const product: Product = { id: 'tee', name: 'Cotton Tee', category: 'clothing', description: 'Everyday cotton tee.', price_cents: 2400, currency: 'USD', color: 'sage', icon: 'shirt', stock: 5, sizes: ['S', 'M'] };
const initial: CartLine[] = [{ product, quantity: 1, size: 'M' }];
const quote: CheckoutQuote = { items: [{ product_id: product.id, name: product.name, quantity: 1, size: 'M', price_cents: 2400, line_total_cents: 2400, stock: 5 }], subtotal_cents: 2400, shipping_cents: 0, tax_cents: 0, total_cents: 2400, currency: 'USD', quote_token: 'quote-1', simulated: true };
const approved: CheckoutResult = { status: 'approved', simulated: true, payment: { reference: 'SIM-TEST', status: 'approved', amount_cents: 2400, currency: 'USD', simulated: true }, order: { id: 'order', number: 'NS-NEW', customer_id: 'customer', status: 'processing', shipping_status: 'Preparing', tracking_number: null, created_at: '2026-10-24', delivered_at: null, total_cents: 2400, currency: 'USD', version: 1, items: [], returns: [], timeline: [], can_cancel: true, can_return: false }, message: 'Practice order created.' };
const declined: CheckoutResult = { ...approved, status: 'declined', order: null, payment: { ...approved.payment, status: 'declined' }, message: 'No order was created.' };
function CartHarness() { const [lines, setLines] = useState(initial); return <Cart lines={lines} setLines={setLines} userId="customer" shop={vi.fn()} orders={vi.fn()} />; }
beforeEach(() => { vi.mocked(api).mockReset(); vi.mocked(post).mockReset(); sessionStorage.clear(); });
afterEach(cleanup);

describe('simulated checkout', () => {
  it('requires server review before explicit confirmation and shows a receipt', async () => {
    vi.mocked(post).mockImplementation(async path => path === '/checkout/quote' ? quote : approved);
    render(<CartHarness />);
    expect(post).not.toHaveBeenCalled();
    expect(screen.queryByRole('button', { name: /Confirm & simulate/ })).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Review order' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Confirm & simulate payment · $24.00' }));
    await screen.findByText('Your demo order is in.');
    expect(post).toHaveBeenNthCalledWith(1, '/checkout/quote', { items: [{ product_id: 'tee', quantity: 1, size: 'M' }] });
    const payment = vi.mocked(post).mock.calls[1][1] as Record<string, unknown>;
    expect(payment.payment_scenario).toBe('approved');
    expect(payment.quote_token).toBe('quote-1');
    expect(payment).not.toHaveProperty('total_cents');
    expect(sessionStorage.getItem('northstar.checkout.customer')).toBeNull();
    expect(screen.getByText('NS-NEW')).toBeTruthy();
  });

  it('keeps declined items and generates a new key only for a new attempt', async () => {
    let payments = 0;
    vi.mocked(post).mockImplementation(async path => path === '/checkout/quote' ? quote : ++payments === 1 ? declined : approved);
    render(<CartHarness />);
    fireEvent.change(screen.getByLabelText('Demo card outcome'), { target: { value: 'declined' } });
    fireEvent.click(screen.getByRole('button', { name: 'Review order' }));
    fireEvent.click(await screen.findByRole('button', { name: /Confirm & simulate/ }));
    await screen.findByText('Simulated payment declined.');
    expect(screen.getByText('Cotton Tee')).toBeTruthy();
    fireEvent.change(screen.getByLabelText('Demo card outcome'), { target: { value: 'approved' } });
    fireEvent.click(screen.getByRole('button', { name: 'Review order' }));
    fireEvent.click(await screen.findByRole('button', { name: /Confirm & simulate/ }));
    await screen.findByText('Your demo order is in.');
    const calls = vi.mocked(post).mock.calls.filter(([path]) => path === '/checkout');
    expect(calls[0][1]).not.toEqual(calls[1][1]);
  });

  it('recovers an unknown result with the exact saved payload after remount', async () => {
    let payments = 0;
    vi.mocked(post).mockImplementation(async path => { if (path === '/checkout/quote') return quote; if (++payments === 1) throw new ApiError('Connection lost.', 0); return approved; });
    const first = render(<CartHarness />);
    fireEvent.click(screen.getByRole('button', { name: 'Review order' }));
    fireEvent.click(await screen.findByRole('button', { name: /Confirm & simulate/ }));
    await screen.findByText(/The payment result is unknown/);
    const stored = JSON.parse(sessionStorage.getItem('northstar.checkout.customer')!);
    first.unmount(); render(<CartHarness />);
    expect(screen.getByLabelText('Demo card outcome').hasAttribute('disabled')).toBe(true);
    fireEvent.click(screen.getByRole('button', { name: 'Retry same payment' }));
    await screen.findByText('Your demo order is in.');
    expect(vi.mocked(post).mock.calls.filter(([path]) => path === '/checkout').map(([, body]) => body)).toEqual([stored, stored]);
  });

  it('invalidates the reviewed total when cart quantities change', async () => {
    vi.mocked(post).mockResolvedValue(quote);
    render(<CartHarness />);
    fireEvent.click(screen.getByRole('button', { name: 'Review order' }));
    await screen.findByRole('button', { name: /Confirm & simulate/ });
    fireEvent.change(screen.getByLabelText('Quantity for Cotton Tee M'), { target: { value: '2' } });
    expect(screen.queryByRole('button', { name: /Confirm & simulate/ })).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Review order' }));
    await waitFor(() => expect(post).toHaveBeenLastCalledWith('/checkout/quote', { items: [{ product_id: 'tee', size: 'M', quantity: 2 }] }));
  });

  it('asks for fresh review after a changed-price or stock conflict', async () => {
    vi.mocked(post).mockImplementation(async path => { if (path === '/checkout/quote') return quote; throw new ApiError('Prices have changed.', 409); });
    render(<CartHarness />);
    fireEvent.click(screen.getByRole('button', { name: 'Review order' }));
    fireEvent.click(await screen.findByRole('button', { name: /Confirm & simulate/ }));
    await screen.findByText(/Prices have changed/);
    expect(screen.getByRole('button', { name: 'Review order' })).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Retry same payment' })).toBeNull();
    expect(sessionStorage.getItem('northstar.checkout.customer')).toBeNull();
  });

  it('prevents adding inventory already in the cart across different sizes', async () => {
    vi.mocked(api).mockResolvedValue([product]);
    render(<Shop lines={[{ product, quantity: 5, size: 'S' }]} setLines={vi.fn()} ask={vi.fn()} openCart={vi.fn()} />);
    await screen.findByText('Cotton Tee');
    fireEvent.change(screen.getByLabelText('Size for Cotton Tee'), { target: { value: 'M' } });
    expect(screen.getByRole('button', { name: 'Add Cotton Tee to cart' }).hasAttribute('disabled')).toBe(true);
  });
});

it('does not offer demo credentials when production demo accounts are disabled', () => {
  const system: System = { version: '0.3.0', llm_mode: 'offline', llm_configured: false, model: null, knowledge_mode: 'tfidf', notice: '', demo_accounts_enabled: false };
  render(<Login system={system} onLogin={vi.fn()} />);
  expect(screen.queryByRole('group', { name: 'Demo account' })).toBeNull();
  expect((screen.getByLabelText('Email address') as HTMLInputElement).value).toBe('');
  expect((screen.getByLabelText('Password') as HTMLInputElement).value).toBe('');
});
