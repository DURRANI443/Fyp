import { useCallback, useEffect, useRef, useState } from 'react';
import type { Dispatch, SetStateAction } from 'react';
import { ApiError, errorText, post } from './api';
import type { CartLine, CheckoutQuote, CheckoutRequest, CheckoutResult, Product } from './types';
import { Badge, Empty, ErrorBox, Icon, label, Loading, money, PageHeading, ProductArt, useResource } from './ui';

export function useCart(userId: string) {
  const storageKey = `northstar.cart.${userId}`;
  const [state, setState] = useState<{ lines: CartLine[]; completed: string[] }>(() => {
    try {
      const saved = JSON.parse(sessionStorage.getItem(storageKey) ?? '[]');
      const lines = Array.isArray(saved) ? saved : saved?.lines;
      return {
        lines: Array.isArray(lines) ? lines.filter((line): line is CartLine => typeof line?.product?.id === 'string' && Number.isInteger(line.quantity) && line.quantity > 0 && line.quantity <= 10 && typeof line.size === 'string').slice(0, 20) : [],
        completed: Array.isArray(saved?.completed) ? saved.completed.filter((key: unknown) => typeof key === 'string').slice(-100) : [],
      };
    } catch { return { lines: [], completed: [] }; }
  });
  useEffect(() => { try { sessionStorage.setItem(storageKey, JSON.stringify(state)); } catch { /* The cart still works in memory. */ } }, [state, storageKey]);
  const setLines: Dispatch<SetStateAction<CartLine[]>> = useCallback(update => {
    setState(previous => ({ ...previous, lines: typeof update === 'function' ? update(previous.lines) : update }));
  }, []);
  const completeCheckout = useCallback((request: CheckoutRequest) => {
    setState(previous => {
      if (previous.completed.includes(request.idempotency_key)) return previous;
      // Keep items added after this payment started, including extra units of the
      // same variant. Duplicate responses from an original request and its retry
      // settle the cart only once, just as the backend settles the order once.
      const lines = previous.lines.flatMap(line => {
        const purchased = request.items.find(item => item.product_id === line.product.id && item.size === line.size)?.quantity ?? 0;
        return line.quantity > purchased ? [{ ...line, quantity: line.quantity - purchased }] : [];
      });
      return { lines, completed: [...previous.completed, request.idempotency_key].slice(-100) };
    });
  }, []);
  return { lines: state.lines, setLines, completeCheckout };
}

function ProductCard({ product, lines, add, ask }: { product: Product; lines: CartLine[]; add: (product: Product, size: string) => void; ask: (message: string) => void }) {
  const [size, setSize] = useState(product.sizes[0] ?? '');
  const quantity = lines.filter(line => line.product.id === product.id).reduce((sum, line) => sum + line.quantity, 0);
  const selectedQuantity = lines.find(line => line.product.id === product.id && line.size === size)?.quantity ?? 0;
  const unavailable = product.stock <= quantity || selectedQuantity >= 10 || !size;
  return <article className="product-card">
    <div className="product-image"><ProductArt product={product} />{product.stock === 0 && <Badge>Out of stock</Badge>}</div>
    <div className="product-category">{label(product.category)}{product.sku && <span> · {product.sku}</span>}</div>
    <div className="product-name"><h3>{product.name}</h3><span>{money(product.price_cents, product.currency)}</span></div>
    <p>{product.description}</p>
    <div className="product-buy"><label>Size<select aria-label={`Size for ${product.name}`} value={size} onChange={e => setSize(e.target.value)}>{product.sizes.map(value => <option key={value}>{value}</option>)}</select></label><button className="button" disabled={unavailable} onClick={() => add(product, size)} aria-label={`Add ${product.name} to cart`}><Icon name="plus" size={15} />{product.stock === 0 ? 'Sold out' : unavailable ? 'Limit reached' : 'Add to cart'}</button></div>
    <div className="product-bottom"><span>{product.stock} in demo stock</span><button className="text-button" onClick={() => ask(`Tell me about ${product.name}.`)}>Ask about this <Icon name="arrow" size={14} /></button></div>
  </article>;
}

export function Shop({ ask, lines, setLines, openCart }: { ask: (message?: string) => void; lines: CartLine[]; setLines: (lines: CartLine[]) => void; openCart: () => void }) {
  const { data, loading, error, reload } = useResource<Product[]>('/products');
  const [category, setCategory] = useState('All essentials');
  const [query, setQuery] = useState('');
  const [notice, setNotice] = useState('');
  const categories = ['All essentials', ...new Set(data?.map(p => p.category))];
  const filtered = data?.filter(p => (category === 'All essentials' || p.category === category) && `${p.name} ${p.description}`.toLowerCase().includes(query.toLowerCase()));
  const add = (product: Product, size: string) => {
    if (lines.length >= 20 && !lines.some(line => line.product.id === product.id && line.size === size)) { setNotice('Your cart can hold 20 different items. Review it before adding more.'); return; }
    const existing = lines.find(line => line.product.id === product.id && line.size === size);
    setLines(existing ? lines.map(line => line === existing ? { ...line, product, quantity: line.quantity + 1 } : line) : [...lines, { product, size, quantity: 1 }]);
    setNotice(`${product.name} added to your cart.`);
  };
  return <>
    <section className="shop-hero"><div className="hero-copy"><div className="eyebrow">THE EVERYDAY COLLECTION</div><h1>Good things.<br />Simply made.</h1><p>Everyday clothing, useful gear, and a little help<br className="desktop-only" /> whenever you need it.</p><button className="button light" onClick={() => document.getElementById('collection')?.scrollIntoView({ behavior: 'smooth' })}>Explore the collection <Icon name="arrow" size={17} /></button><span className="hero-footnote">Demo prices and inventory. All payments are simulated.</span></div><div className="hero-art"><div className="hero-circle" /><ProductArt product={data?.find(p => p.icon === 'bag') ?? { name: 'Everyday tote', icon: 'bag', color: '#d4bf91' }} /><div className="hero-tag"><Icon name="spark" size={16} /> Made for the everyday</div></div></section>
    <section className="service-strip"><span><Icon name="box" /> Free demo delivery</span><span><Icon name="shield" /> No real payments</span><button onClick={() => ask()}><Icon name="chat" /> Help with every order <Icon name="arrow" size={16} /></button></section>
    {notice && <div className="success-box cart-notice" role="status"><Icon name="check" /><span>{notice}</span><button className="text-button" onClick={openCart}>View cart <Icon name="arrow" size={15} /></button></div>}
    <div className="collection-heading" id="collection"><div><div className="eyebrow">YOUR NEXT EVERYDAY FAVORITE</div><h2>The essentials</h2></div><label className="search-input"><Icon name="search" size={17} /><input aria-label="Search products" placeholder="Find something good" value={query} onChange={e => setQuery(e.target.value)} /></label></div>
    <div className="filter-row">{categories.map(c => <button key={c} className={`filter-pill ${c === category ? 'active' : ''}`} onClick={() => setCategory(c)}>{label(c)}</button>)}<span className="filter-count">{filtered?.length ?? 0} pieces</span></div>
    <ErrorBox message={error} retry={reload} />{loading ? <Loading text="Opening the collection…" /> : <div className="product-grid">{filtered?.map(product => <ProductCard key={product.id} product={product} lines={lines} add={add} ask={ask} />)}</div>}
    {!loading && !error && !filtered?.length && <Empty title="No essentials found" icon="search">Try another name or category.</Empty>}
    <div className="shop-note"><Icon name="spark" size={21} /><div><strong>Your shopping companion is here.</strong><p>Ask about a product, store policies, or an order. Product photos illustrate the demo collection.</p><a href="/products/credits.html" target="_blank" rel="noreferrer">Photo credits</a></div><button className="button secondary" onClick={() => ask()}>Let’s talk <Icon name="arrow" size={16} /></button></div>
  </>;
}

const demoShipping = { name: 'Demo Customer', address: '123 Demo Street', city: 'Demo City', postal_code: '00000', country: 'Demo Country' };

export function Cart({ lines, setLines, completeCheckout, userId, shop, orders }: { lines: CartLine[]; setLines: (lines: CartLine[]) => void; completeCheckout: (request: CheckoutRequest) => void; userId: string; shop: () => void; orders: () => void }) {
  const pendingKey = `northstar.checkout.${userId}`;
  const [quote, setQuote] = useState<CheckoutQuote | null>(null);
  const [scenario, setScenario] = useState<'approved' | 'declined'>('approved');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<CheckoutResult | null>(null);
  const [attempt, setAttempt] = useState<CheckoutRequest | null>(() => {
    try { const value = JSON.parse(sessionStorage.getItem(pendingKey) ?? 'null'); return value?.idempotency_key && value?.quote_token && Array.isArray(value.items) ? value : null; } catch { return null; }
  });
  const submitting = useRef(false);
  const mounted = useRef(true);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  const items = lines.map(line => ({ product_id: line.product.id, quantity: line.quantity, size: line.size }));
  const update = (next: CartLine[]) => { setLines(next); setQuote(null); setResult(null); setError(''); };
  const saveAttempt = (value: CheckoutRequest | null) => {
    setAttempt(value);
    try { if (value) sessionStorage.setItem(pendingKey, JSON.stringify(value)); else sessionStorage.removeItem(pendingKey); } catch { /* In-memory retries still keep the same key. */ }
  };
  const review = async () => {
    if (submitting.current) return;
    submitting.current = true; setBusy(true); setError(''); setResult(null);
    try { const value = await post<CheckoutQuote>('/checkout/quote', { items }); if (mounted.current) setQuote(value); }
    catch (e) { if (mounted.current) setError(errorText(e)); }
    finally { submitting.current = false; if (mounted.current) setBusy(false); }
  };
  const pay = async () => {
    if (submitting.current || (!quote && !attempt)) return;
    const request = attempt ?? { items, shipping: demoShipping, payment_scenario: scenario, quote_token: quote!.quote_token, idempotency_key: crypto.randomUUID() };
    saveAttempt(request); submitting.current = true; setBusy(true); setError('');
    try {
      const value = await post<CheckoutResult>('/checkout', request);
      // Complete the saved request even if the user navigated away while it was in flight.
      try {
        const saved = JSON.parse(sessionStorage.getItem(pendingKey) ?? 'null');
        if (saved?.idempotency_key === request.idempotency_key) sessionStorage.removeItem(pendingKey);
      } catch { /* Storage is optional. */ }
      if (value.status === 'approved') completeCheckout(request);
      if (mounted.current) { setAttempt(null); setResult(value); if (value.status === 'declined') setQuote(null); }
    } catch (e) {
      if (mounted.current) {
        if (e instanceof ApiError && e.status >= 400 && e.status < 500) { saveAttempt(null); setQuote(null); setError(`${errorText(e)} Review the cart again before paying.`); }
        else setError(`${errorText(e)} The payment result is unknown. Use “Retry same payment” to safely retrieve or finish this attempt.`);
      }
    } finally { submitting.current = false; if (mounted.current) setBusy(false); }
  };
  const estimatedTotal = lines.reduce((sum, line) => sum + line.product.price_cents * line.quantity, 0);
  if (result?.status === 'approved' && result.order) return <>
    <PageHeading eyebrow="PRACTICE PURCHASE COMPLETE" title="Your demo order is in." subtitle="No real money was charged and no physical delivery will take place." />
    <section className="panel checkout-receipt"><div className="confirmation-icon"><Icon name="check" size={28} /></div><Badge tone="green">Simulated payment approved</Badge><h2>{result.order.number}</h2><p>{result.message}</p><div className="info-box"><strong>{money(result.payment.amount_cents, result.payment.currency)} · Demo card</strong><span>Payment reference: {result.payment.reference}</span><span>Demo delivery: {demoShipping.address}, {demoShipping.city}</span></div><div className="modal-actions"><button className="button secondary" onClick={shop}>Continue shopping</button><button className="button" onClick={orders}>View my orders <Icon name="arrow" size={16} /></button></div></section>
  </>;
  return <>
    <PageHeading eyebrow="A FEW EVERYDAY FAVORITES" title="Your cart" subtitle="Review your items, then try a clearly simulated payment." action={<button className="text-button" onClick={shop}>Continue shopping <Icon name="arrow" size={15} /></button>} />
    <div className="demo-checkout-banner"><Icon name="shield" /><div><strong>Practice checkout only</strong><span>Demo prices, inventory, shipping and payment. No real card details or money are used.</span></div></div>
    {attempt && <div className="info-box" role="status"><strong>A payment attempt is awaiting confirmation.</strong><span>Retrying uses the original cart, shipping details and payment choice. It cannot create a duplicate order.</span><button className="button" disabled={busy} onClick={pay}>{busy ? 'Checking payment…' : 'Retry same payment'}</button></div>}
    <ErrorBox message={error} />
    {result?.status === 'declined' && <div className="error-box" role="alert"><span><strong>Simulated payment declined.</strong> {result.message} Your cart is saved. Choose approval and review again to retry.</span></div>}
    {!lines.length && !attempt ? <Empty title="Your cart is waiting" icon="shop"><p>Add something from the collection to try the complete order flow.</p><button className="button" onClick={shop}>Browse the collection</button></Empty> : <div className="checkout-layout">
      <section className="panel cart-items" aria-label="Cart items">{lines.map((line, index) => <div className="cart-line" key={`${line.product.id}-${line.size}`}><ProductArt product={line.product} compact /><div className="cart-line-copy"><strong>{line.product.name}</strong><span>{line.size} · {money(line.product.price_cents, line.product.currency)} each</span><button className="text-button danger-text" disabled={busy || !!attempt} onClick={() => update(lines.filter((_, n) => n !== index))} aria-label={`Remove ${line.product.name} ${line.size}`}>Remove</button></div><label>Qty<select aria-label={`Quantity for ${line.product.name} ${line.size}`} disabled={busy || !!attempt} value={line.quantity} onChange={e => update(lines.map((item, n) => n === index ? { ...item, quantity: Number(e.target.value) } : item))}>{Array.from({ length: Math.min(10, Math.max(line.quantity, line.product.stock - lines.filter(other => other.product.id === line.product.id && other !== line).reduce((sum, other) => sum + other.quantity, 0))) }, (_, n) => <option key={n + 1}>{n + 1}</option>)}</select></label><b>{money(line.product.price_cents * line.quantity, line.product.currency)}</b></div>)}</section>
      <section className="panel checkout-summary"><h2>Order summary</h2><div className="summary-row"><span>{quote ? 'Subtotal' : 'Estimated subtotal'}</span><strong>{money(quote?.subtotal_cents ?? estimatedTotal, quote?.currency ?? 'USD')}</strong></div><div className="summary-row"><span>Demo delivery</span><span>{money(quote?.shipping_cents ?? 0)}</span></div><div className="summary-row"><span>Demo tax</span><span>{money(quote?.tax_cents ?? 0)}</span></div><div className="order-total"><span>{quote ? 'Confirmed total' : 'Estimated total'}</span><strong>{money(quote?.total_cents ?? estimatedTotal, quote?.currency ?? 'USD')}</strong></div>
        {quote && <p className="quote-note">Prices and availability checked by the store. They are checked again when you confirm.</p>}
        <div className="info-box"><strong>Demo shipping address</strong><span>{demoShipping.name}<br />{demoShipping.address}<br />{demoShipping.city}, {demoShipping.postal_code}<br />{demoShipping.country}</span><small>This synthetic address is used for every practice order.</small></div>
        <label className="payment-choice">Demo card outcome<select aria-label="Demo card outcome" disabled={busy || !!attempt} value={scenario} onChange={e => setScenario(e.target.value as 'approved' | 'declined')}><option value="approved">Approve payment</option><option value="declined">Decline payment</option></select></label>
        {!attempt && <button className="button checkout-submit" disabled={busy || !lines.length} onClick={quote ? pay : review}>{busy ? quote ? 'Processing demo payment…' : 'Checking prices…' : quote ? `Confirm & simulate payment · ${money(quote.total_cents, quote.currency)}` : 'Review order'}</button>}
      </section>
    </div>}
  </>;
}
