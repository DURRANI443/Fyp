import { useEffect, useRef, useState } from 'react';
import { api, ApiError, errorText, post } from './api';
import type { Conversation, Order, Proposal } from './types';
import { Badge, date, Empty, ErrorBox, Icon, label, Loading, MessageBubble, Modal, money, PageHeading, ProductArt, useResource } from './ui';

export { Shop } from './store';

export function ProposalConfirmation({ proposal, busy, error, onConfirm, onClose }: { proposal: Proposal; busy: boolean; error: string; onConfirm: () => void; onClose: () => void }) {
  return <Modal title={proposal.kind === 'cancel_order' ? 'Confirm cancellation' : 'Confirm return request'} onClose={() => { if (!busy) onClose(); }}><div className="modal-body"><div className="confirmation-icon"><Icon name="shield" size={27} /></div><p className="confirmation-summary">{proposal.summary}</p><div className="info-box"><strong>Order {proposal.order_number}</strong><span>{proposal.kind === 'cancel_order' ? 'Confirming will cancel this order if it is still eligible.' : 'Confirming submits a request for the returns team to review.'}</span><small>Confirmation expires {date(proposal.expires_at, true)}.</small></div><ErrorBox message={error} /><div className="modal-actions"><button className="button secondary" onClick={onClose} disabled={busy}>Go back</button><button className="button" onClick={onConfirm} disabled={busy}>{busy ? 'Confirming…' : proposal.kind === 'cancel_order' ? 'Confirm cancellation' : 'Submit return request'}</button></div></div></Modal>;
}

function OrderRequest({ order, kind, close, done }: { order: Order; kind: Proposal['kind']; close: () => void; done: () => void }) {
  const returnableItems = order.items.map(item => ({ ...item, remaining: item.returnable_quantity ?? Math.max(0, item.quantity - order.returns.filter(r => r.item_id === item.id && ['requested', 'approved'].includes(r.status)).reduce((sum, r) => sum + r.quantity, 0)) })).filter(item => item.remaining > 0);
  const [itemId, setItemId] = useState(returnableItems[0]?.id ?? '');
  const [quantity, setQuantity] = useState(1);
  const [reason, setReason] = useState('');
  const [proposal, setProposal] = useState<Proposal | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const key = useRef(crypto.randomUUID());
  const create = async (event: React.FormEvent) => {
    event.preventDefault(); setBusy(true); setError('');
    try { setProposal(await post<Proposal>('/action-proposals', { kind, order_id: order.id, ...(kind === 'create_return_request' ? { item_id: itemId, quantity } : {}), reason })); }
    catch (e) { setError(errorText(e)); } finally { setBusy(false); }
  };
  const confirm = async () => {
    setBusy(true); setError('');
    try { await post(`/action-proposals/${proposal!.id}/confirm`, { idempotency_key: key.current }); done(); }
    catch (e) { setError(errorText(e)); } finally { setBusy(false); }
  };
  if (proposal) return <ProposalConfirmation proposal={proposal} busy={busy} error={error} onConfirm={confirm} onClose={close} />;
  return <Modal title={kind === 'cancel_order' ? 'Cancel your order' : 'Start a return'} onClose={() => { if (!busy) close(); }}><form className="modal-body form-stack" onSubmit={create}><p>Let’s check the available options for <strong>{order.number}</strong>.</p>{kind === 'create_return_request' && <><label>Item<select value={itemId} onChange={e => { setItemId(e.target.value); setQuantity(1); }}>{returnableItems.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><label>Quantity<input type="number" min={1} max={Math.min(100, returnableItems.find(i => i.id === itemId)?.remaining ?? 1)} value={quantity} onChange={e => setQuantity(Number(e.target.value))} required /></label></>}<label>{kind === 'cancel_order' ? 'Reason (optional)' : 'Reason for return'}<textarea rows={3} required={kind === 'create_return_request'} maxLength={500} placeholder="Tell us a little more…" value={reason} onChange={e => setReason(e.target.value)} /></label><ErrorBox message={error} /><div className="modal-actions"><button type="button" className="button secondary" onClick={close} disabled={busy}>Keep order</button><button className="button" disabled={busy || (kind === 'create_return_request' && !returnableItems.length)}>{busy ? 'Checking eligibility…' : 'Review request'}<Icon name="arrow" size={16} /></button></div></form></Modal>;
}

export function Orders({ ask }: { ask: (message?: string) => void }) {
  const { data, loading, error, reload } = useResource<Order[]>('/orders');
  const [selected, setSelected] = useState<string | null>(null);
  const [request, setRequest] = useState<{ order: Order; kind: Proposal['kind'] } | null>(null);
  const [notice, setNotice] = useState('');
  const order = data?.find(o => o.id === selected) ?? data?.[0];
  return <><PageHeading eyebrow="ALL THE LITTLE DETAILS" title="Your orders" subtitle="Follow your essentials from our door to yours." /><ErrorBox message={error} retry={reload} />{notice && <div className="success-box" role="status"><Icon name="check" />{notice}<button aria-label="Dismiss confirmation" className="icon-button" onClick={() => setNotice('')}><Icon name="close" size={15} /></button></div>}{loading ? <Loading /> : !data?.length ? <Empty title="Your order story starts here" icon="box">Orders linked to your account will appear here.</Empty> : <div className="orders-layout"><div className="order-list">{data.map(o => <button className={`order-list-card ${order?.id === o.id ? 'selected' : ''}`} key={o.id} onClick={() => setSelected(o.id)}><div><strong>{o.number}</strong><Badge tone={o.status === 'delivered' ? 'green' : ''}>{label(o.status)}</Badge></div><span>{date(o.created_at)}</span><div className="order-preview"><ProductArt compact product={o.items[0] ?? { name: 'Order', color: '#8b9f8f', icon: 'box' }} /><div><b>{o.items[0]?.name}</b><small>{o.items.length} {o.items.length === 1 ? 'item' : 'items'} · {money(o.total_cents, o.currency)}</small></div><Icon name="arrow" size={17} /></div></button>)}</div>{order && <section className="panel order-detail"><div className="panel-heading"><div><span className="eyebrow">ORDER DETAILS</span><h2>{order.number}</h2></div><Badge tone={order.status === 'delivered' ? 'green' : ''}>{label(order.status)}</Badge></div><div className="delivery-card"><Icon name="box" size={25} /><div><strong>{order.shipping_status}</strong><p>{order.tracking_number ? `Tracking reference: ${order.tracking_number}` : 'Tracking details appear when your order ships.'}</p></div></div><ol className="timeline">{order.timeline.map((t, i) => <li key={`${t.label}-${i}`} className={t.complete ? 'complete' : ''}><span className="timeline-point">{t.complete && <Icon name="check" size={12} />}</span><div><strong>{t.label}</strong><small>{t.at ? date(t.at, true) : t.complete ? 'Confirmed' : 'Pending'}</small></div></li>)}</ol><h3 className="section-title">What’s inside</h3>{order.items.map(item => <div className="order-item" key={item.id}><ProductArt compact product={item} /><div><strong>{item.name}</strong><span>Quantity {item.quantity}{item.size ? ` · ${item.size}` : ''}</span></div><b>{money(item.price_cents * item.quantity, order.currency)}</b></div>)}<div className="order-total"><span>Order total</span><strong>{money(order.total_cents, order.currency)}</strong></div>{order.payment && <div className="info-box payment-detail"><strong>Simulated payment: {label(order.payment.status)}</strong><span>Reference: {order.payment.reference}</span><small>No real money was charged. This is a practice order.</small></div>}{order.returns.length > 0 && <div className="return-list"><h3 className="section-title">Return requests</h3>{order.returns.map(r => <div key={r.id}><span>{order.items.find(i => i.id === r.item_id)?.name ?? 'Item'} × {r.quantity}</span><Badge>{label(r.status)}</Badge><small>{r.reason}</small></div>)}</div>}<div className="order-actions"><button className="button secondary" onClick={() => ask(`I need help with order ${order.number}.`)}><Icon name="chat" size={17} />Get order help</button>{order.can_cancel && <button className="text-button" onClick={() => setRequest({ order, kind: 'cancel_order' })}>Cancel order</button>}{order.can_return && <button className="text-button" onClick={() => setRequest({ order, kind: 'create_return_request' })}>Start a return <Icon name="arrow" size={15} /></button>}</div></section>}</div>}{request && <OrderRequest {...request} close={() => setRequest(null)} done={() => { setNotice(request.kind === 'cancel_order' ? 'Your cancellation was confirmed.' : 'Your return request was submitted for review.'); setRequest(null); reload(); }} />}</>;
}

export function Support({ initialMessage, consumeInitial }: { initialMessage: string | null; consumeInitial: () => void }) {
  const list = useResource<Conversation[]>('/conversations');
  const [selected, setSelected] = useState<string | null>(null);
  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [draft, setDraft] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [conversationRevision, setConversationRevision] = useState(0);
  const [busy, setBusy] = useState(false);
  const [confirming, setConfirming] = useState<Proposal | null>(null);
  const [confirmError, setConfirmError] = useState('');
  const [confirmBusy, setConfirmBusy] = useState(false);
  const sendKey = useRef<{ text: string; id: string } | null>(null);
  const confirmKey = useRef(crypto.randomUUID());
  const end = useRef<HTMLDivElement>(null);
  const consumed = useRef(false);
  useEffect(() => {
    if (initialMessage !== null && !consumed.current) { consumed.current = true; setDraft(initialMessage); consumeInitial(); }
  }, [initialMessage, consumeInitial]);
  useEffect(() => {
    if (!selected) { setConversation(null); setLoading(false); return; }
    if (conversation?.id === selected) { setLoading(false); return; }
    const controller = new AbortController(); setConversation(null); setLoading(true); setError('');
    api<Conversation>(`/conversations/${selected}`, { signal: controller.signal }).then(setConversation).catch(e => { if (!controller.signal.aborted) setError(errorText(e)); }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [selected, conversationRevision]);
  useEffect(() => {
    if (!selected || !conversation || !['human_owned', 'handoff_pending'].includes(conversation.mode) || busy) return;
    const controller = new AbortController();
    let pending = false;
    const id = window.setInterval(async () => {
      if (pending || controller.signal.aborted) return;
      pending = true;
      try {
        const next = await api<Conversation>(`/conversations/${selected}`, { signal: controller.signal });
        if (!controller.signal.aborted) setConversation(next);
      } catch (e) {
        if (!controller.signal.aborted && !(e instanceof DOMException && e.name === 'AbortError')) {
          setError(errorText(e));
          if (e instanceof ApiError && [401, 403, 404].includes(e.status)) { window.clearInterval(id); controller.abort(); }
        }
      } finally { pending = false; }
    }, 4000);
    return () => { controller.abort(); window.clearInterval(id); };
  }, [selected, conversation?.mode, busy]);
  useEffect(() => { end.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }); }, [conversation?.messages.length, busy]);
  const send = async (content = draft) => {
    if (!content.trim() || busy || loading || (selected && conversation?.id !== selected) || conversation?.mode === 'closed') return;
    setBusy(true); setError('');
    try {
      let current = conversation;
      if (!current) { current = await post<Conversation>('/conversations', {}); setConversation(current); setSelected(current.id); }
      if (sendKey.current?.text !== content) sendKey.current = { text: content, id: crypto.randomUUID() };
      const next = await post<Conversation>(`/conversations/${current.id}/messages`, { content: content.trim(), client_message_id: sendKey.current.id });
      setConversation(next); setDraft(''); sendKey.current = null; list.reload();
    } catch (e) { setError(errorText(e)); } finally { setBusy(false); }
  };
  const handoff = async () => {
    setBusy(true); setError('');
    try {
      const current = conversation ?? await post<Conversation>('/conversations', {});
      const next = await post<Conversation>(`/conversations/${current.id}/handoff`);
      setSelected(current.id); setConversation(next); list.reload();
    } catch (e) { setError(errorText(e)); } finally { setBusy(false); }
  };
  const confirm = async () => {
    setConfirmBusy(true); setConfirmError('');
    try { await post(`/action-proposals/${confirming!.id}/confirm`, { idempotency_key: confirmKey.current }); setConversation(await api<Conversation>(`/conversations/${selected}`)); setConfirming(null); list.reload(); }
    catch (e) { setConfirmError(errorText(e)); } finally { setConfirmBusy(false); }
  };
  const human = conversation && ['handoff_pending', 'human_owned'].includes(conversation.mode);
  const unavailableSelection = !!selected && conversation?.id !== selected;
  return <><PageHeading eyebrow="HERE FOR THE EVERYDAY QUESTIONS" title="A little help, right here." subtitle="Order updates, product questions, or a person to talk to. Start a conversation." /><div className="support-layout"><aside className="conversation-sidebar"><button className="button new-conversation" disabled={busy} onClick={() => { setSelected(null); setConversation(null); setDraft(''); setError(''); sendKey.current = null; }}><Icon name="plus" size={16} />New conversation</button><div className="sidebar-section-title">YOUR CONVERSATIONS</div><ErrorBox message={list.error} retry={list.reload} />{list.loading && !list.data ? <Loading text="Loading…" /> : list.data?.length ? list.data.map(c => <button key={c.id} disabled={busy} className={`conversation-item ${selected === c.id ? 'selected' : ''}`} onClick={() => { setSelected(c.id); setDraft(''); }}><div><Icon name="chat" size={16} /><strong>{c.title}</strong></div><p>{c.preview || 'Conversation started'}</p><span>{date(c.updated_at)}<i className={c.mode === 'human_owned' ? 'human-dot' : ''} /></span></button>) : <p className="muted small sidebar-hint">Your conversations will be saved here, so you can pick up where you left off.</p>}<div className="support-sidebar-note"><Icon name="shield" size={21} /><strong>Help with a human touch</strong><p>Ask for our support team whenever you need a little extra help.</p></div></aside><section className="chat-panel"><header className="chat-header"><div className="assistant-avatar"><Icon name={human ? 'person' : 'spark'} size={22} /></div><div><strong>{conversation?.mode === 'closed' ? 'Conversation closed' : human ? 'Northstar support team' : 'Northstar assistant'}</strong><span>{conversation?.mode === 'closed' ? 'Start a new conversation for more help' : human ? conversation.ticket?.assignee_name ? `Connected with ${conversation.ticket.assignee_name}` : 'Waiting for a team member' : 'Order support & everyday answers'}</span></div><Badge tone={human ? 'amber' : 'green'}>{conversation?.mode === 'closed' ? 'Resolved' : human ? 'Human support' : 'Ready to help'}</Badge>{!human && conversation?.mode !== 'closed' && <button className="text-button handoff-button" onClick={handoff} disabled={busy || loading || unavailableSelection}>Talk to a person</button>}</header>{human && <div className="handoff-notice"><Icon name="users" size={17} /><span>Your conversation is with our {conversation.ticket?.team ?? 'support'} team. New messages go to a person; automatic replies are paused.</span></div>}<div className="chat-scroll">{loading ? <Loading text="Opening conversation…" /> : !conversation?.messages.length ? <div className="chat-welcome"><div className="welcome-spark"><Icon name="spark" size={35} /></div><div className="eyebrow">A GOOD PLACE TO START</div><h2>What can we help you with?</h2><p>Ask a question in your own words, or start with one of these.</p><div className="suggestion-grid">{[{ icon: 'box', title: 'Track my order', text: 'Where is my order?' }, { icon: 'shield', title: 'Returns & exchanges', text: 'What is your return policy?' }, { icon: 'shop', title: 'Find my next favorite', text: 'Help me find a product.' }, { icon: 'chat', title: 'Shipping questions', text: 'What is your shipping policy?' }].map(s => <button disabled={busy} key={s.title} onClick={() => { setDraft(s.text); }}><Icon name={s.icon} /><span>{s.title}</span><Icon name="arrow" size={14} /></button>)}</div></div> : <div className="messages">{conversation.messages.map(m => <MessageBubble key={m.id} message={m} />)}{conversation.proposals?.filter(p => p.status === 'pending').map(p => <div className="proposal-card" key={p.id}><Icon name="shield" size={22} /><div><strong>Your confirmation is needed</strong><p>{p.summary}</p><button className="button small-button" onClick={() => { confirmKey.current = crypto.randomUUID(); setConfirmError(''); setConfirming(p); }} disabled={busy}>Review & confirm <Icon name="arrow" size={14} /></button></div></div>)}</div>}{busy && <div className="thinking" role="status"><span /><span /><span />One moment…</div>}<div ref={end} /></div><div className="chat-composer"><ErrorBox message={error} retry={unavailableSelection ? () => setConversationRevision(n => n + 1) : undefined} /><form onSubmit={e => { e.preventDefault(); void send(); }}><textarea aria-label="Message" placeholder={conversation?.mode === 'closed' ? 'This conversation is closed. Start a new conversation.' : human ? 'Write to the support team…' : 'Ask about an order, product, or policy…'} value={draft} maxLength={3000} onChange={e => setDraft(e.target.value)} rows={2} disabled={loading || busy || unavailableSelection || conversation?.mode === 'closed'} onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); void send(); } }} /><button className="send-button" aria-label="Send message" disabled={!draft.trim() || busy || loading || unavailableSelection || conversation?.mode === 'closed'}><Icon name="send" size={19} /></button></form><div className="composer-caption"><span>Order actions always need your confirmation.</span><span>Enter to send · Shift + Enter for a new line</span></div></div></section></div>{confirming && <ProposalConfirmation proposal={confirming} busy={confirmBusy} error={confirmError} onConfirm={confirm} onClose={() => { if (!confirmBusy) setConfirming(null); }} />}</>;
}
