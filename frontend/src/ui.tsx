import { useEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { api, errorText } from './api';
import type { Message, Product } from './types';

export const money = (cents: number, currency = 'USD') => new Intl.NumberFormat('en-US', { style: 'currency', currency }).format(cents / 100);
export const date = (value: string | null, time = false) => value ? new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', ...(time ? { hour: 'numeric', minute: '2-digit' } : { year: 'numeric' }) }).format(new Date(value)) : 'Not yet';
export const label = (value: string) => value.replaceAll('_', ' ').replace(/\b\w/g, c => c.toUpperCase());
export function useResource<T>(path: string | null) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    if (!path) { setLoading(false); setData(null); return; }
    const controller = new AbortController();
    setLoading(true); setError('');
    api<T>(path, { signal: controller.signal }).then(setData).catch(e => { if (!controller.signal.aborted) setError(errorText(e)); }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [path, revision]);
  return { data, setData, loading, error, reload: () => setRevision(n => n + 1) };
}
export function Icon({ name = 'spark', size = 20 }: { name?: string; size?: number }) {
  const paths: Record<string, ReactNode> = {
    spark: <path d="m12 2 2.8 7.2L22 12l-7.2 2.8L12 22l-2.8-7.2L2 12l7.2-2.8Z" />,
    shop: <><path d="M3 9h18l-2-6H5L3 9Zm1 0v12h16V9M9 21v-7h6v7" /><path d="M3 9c0 4 5 4 5 0 0 4 8 4 8 0 0 4 5 4 5 0" /></>,
    box: <><path d="m3 7 9-5 9 5v10l-9 5-9-5V7Zm0 0 9 5 9-5M12 12v10M7 4.8l9 5" /></>,
    chat: <path d="M21 11a8 8 0 0 1-8 8H8l-5 3V7a4 4 0 0 1 4-4h6a8 8 0 0 1 8 8ZM7 8h10M7 12h7" />,
    inbox: <><path d="M4 4h16l2 12v4H2v-4L4 4Z" /><path d="M2 15h6l2 3h4l2-3h6M8 8h8M8 11h8" /></>,
    book: <><path d="M12 5c-3-3-7-2-10-1v16c3-1 7-2 10 1 3-3 7-2 10-1V4c-3-1-7-2-10 1Zm0 0v16" /></>,
    users: <><circle cx="9" cy="7" r="4" /><path d="M2 22v-4a7 7 0 0 1 14 0v4M17 3a4 4 0 0 1 0 8M19 14a6 6 0 0 1 3 5v3" /></>,
    chart: <><path d="M4 3v18h18M8 16v-5M13 16V7M18 16V3" /></>,
    arrow: <path d="M4 12h16m-6-6 6 6-6 6" />,
    send: <><path d="m3 3 19 9-19 9 3-9-3-9Zm3 9h16" /></>,
    plus: <path d="M12 4v16M4 12h16" />,
    search: <><circle cx="10" cy="10" r="7" /><path d="m15 15 6 6" /></>,
    check: <path d="m4 12 5 5L20 6" />,
    close: <path d="m6 6 12 12M18 6 6 18" />,
    logout: <><path d="M10 3H3v18h7M8 12h14m-5-5 5 5-5 5" /></>,
    clock: <><circle cx="12" cy="12" r="9" /><path d="M12 6v6l4 2" /></>,
    shield: <><path d="m12 2 9 4v6c0 6-9 10-9 10S3 18 3 12V6l9-4Z" /><path d="m8 12 3 3 5-6" /></>,
    person: <><circle cx="12" cy="7" r="4" /><path d="M4 22v-3a8 8 0 0 1 16 0v3" /></>,
  };
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name] ?? paths.spark}</svg>;
}
export function Badge({ children, tone = '' }: { children: ReactNode; tone?: string }) { return <span className={`badge ${tone}`}>{children}</span>; }
export function ErrorBox({ message, retry }: { message: string; retry?: () => void }) { return message ? <div className="error-box" role="alert"><span>{message}</span>{retry && <button className="text-button" onClick={retry}>Try again</button>}</div> : null; }
export function Loading({ text = 'Loading your workspace…' }: { text?: string }) { return <div className="loading" role="status"><span className="spinner" />{text}</div>; }
export function Empty({ title, children, icon = 'inbox' }: { title: string; children?: ReactNode; icon?: string }) { return <div className="empty"><div className="empty-icon"><Icon name={icon} size={28} /></div><h3>{title}</h3><div>{children}</div></div>; }
export function PageHeading({ eyebrow, title, subtitle, action }: { eyebrow: string; title: string; subtitle: string; action?: ReactNode }) { return <div className="page-heading"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1><p>{subtitle}</p></div>{action}</div>; }
export function Modal({ title, children, onClose }: { title: string; children: ReactNode; onClose: () => void }) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => { ref.current?.showModal(); return () => ref.current?.close(); }, []);
  return <dialog ref={ref} className="modal" onCancel={e => { e.preventDefault(); onClose(); }} onClick={e => { if (e.target === ref.current) onClose(); }}><div className="modal-header"><h2>{title}</h2><button className="icon-button" aria-label="Close dialog" onClick={onClose}><Icon name="close" /></button></div>{children}</dialog>;
}
export function ProductArt({ product, compact = false }: { product: Pick<Product, 'name' | 'color' | 'icon'> & Partial<Pick<Product, 'image_url' | 'image_alt'>>; compact?: boolean }) {
  const [failed, setFailed] = useState(false);
  useEffect(() => setFailed(false), [product.image_url]);
  if (product.image_url && !failed) return <div className={`product-art product-photo ${compact ? 'compact' : ''}`}><img src={product.image_url} alt={product.image_alt || product.name} loading="lazy" onError={() => setFailed(true)} /></div>;
  const type = `${product.icon} ${product.name}`.toLowerCase();
  const palette: Record<string, string> = { sage: '#8b9f8b', sand: '#c6b491', cream: '#c8c3ac', blue: '#8196a7', olive: '#81886b', rose: '#b99891' };
  const color = /^#[0-9a-f]{3,8}$/i.test(product.color) ? product.color : palette[product.color] ?? '#7f978c';
  return <div className={`product-art ${compact ? 'compact' : ''}`} style={{ backgroundColor: `${color}19` }}><svg viewBox="0 0 280 240" role="img" aria-label={product.name}>
    <ellipse cx="140" cy="205" rx="79" ry="10" fill="#18372e" opacity=".08" />
    {(/scarf/.test(type)) ? <g><path d="M88 45q50-14 83 0l-9 82 32 61-40 20-29-64 12-72-15 126-40-4Z" fill={color}/><path d="m86 186 37 5m34 8 31-15M101 51 91 178m22-125-9 128m45-125-9 75 25 58" stroke="#fffdf4" opacity=".28" fill="none" strokeWidth="3"/><path d="m83 192-1 12m12-11-1 12m12-10-1 12m12-11-1 12m42-6 5 10m7-15 5 10m6-15 5 10" stroke={color} strokeWidth="4"/></g> : (/shoe|sneaker|trainer/.test(type)) ? <g><path d="m67 112 41 17 29-37 32 35 46 27q30 12 23 35H51q-16-14-6-33Z" fill={color} /><path d="M44 181h195v15q-2 11-19 11H57q-16-2-15-12Z" fill="#fffdf5" stroke="#d3d3cb" strokeWidth="2" /><path d="m126 111 24 9m-34 3 25 9m-35 3 25 9" stroke="#fffdf5" strokeWidth="5" /><path d="m65 127 20 13-15 31H49" fill="#fff" opacity=".25" /></g> : (/bag|tote|backpack/.test(type)) ? <g><path d="M94 82V68a46 46 0 0 1 92 0v14" fill="none" stroke={color} strokeWidth="12" /><path d="M75 73h130l12 124H63Z" fill={color} /><path d="M90 90v89M190 90v89" stroke="white" opacity=".25" strokeWidth="3" /><rect x="117" y="131" width="46" height="27" rx="3" fill="#faf9f0" /><path d="m140 137 3 5 6 2-6 2-3 6-2-6-6-2 6-2Z" fill={color} /></g> : (/cap|hat/.test(type)) ? <g><path d="M66 142a74 74 0 0 1 148 0Z" fill={color} /><path d="M67 140h141l40 26q-35 34-117 5l-64-9Z" fill={color} /><path d="M142 70q-28 25-19 72M67 142h145" stroke="white" opacity=".25" fill="none" strokeWidth="3" /></g> : (/pant|trouser|jean/.test(type)) ? <g><path d="M91 42h98l9 158h-47l-11-105-11 105H82Z" fill={color} /><path d="M92 58h96M140 45v41M100 59q5 23-14 30m96-30q-5 23 11 30" fill="none" stroke="white" opacity=".3" strokeWidth="2" /></g> : <g><path d="m103 46-39 19-31 57 35 21 22-31-5 89h110l-5-89 22 31 35-21-31-57-39-19Z" fill={color} /><path d="M108 48q32 27 64 0" fill="none" stroke="#fffdf5" opacity=".6" strokeWidth="8" /><path d="M90 112 96 77m94 35-6-35M87 191h106" stroke="#fff" opacity=".18" strokeWidth="3" /><path d="m150 91 3 7 8 3-8 3-3 8-3-8-8-3 8-3Z" fill="#fffdf5" opacity=".7" /></g>}
  </svg></div>;
}
export function MessageBubble({ message, customerName }: { message: Message; customerName?: string }) {
  const isUser = message.role === 'user';
  return <article className={`message ${isUser ? 'from-user' : ''} ${message.role === 'system' ? 'system-message' : ''}`}><div className="message-meta"><span>{isUser ? customerName ?? 'You' : message.sender_name || (message.role === 'staff' ? 'Support team' : message.role === 'system' ? 'Conversation update' : 'Northstar assistant')}</span><time dateTime={message.created_at}>{date(message.created_at, true)}</time></div><div className="message-bubble">{message.content}</div>{message.citations?.length > 0 && <div className="citations">{message.citations.map(c => <span key={`${c.id}-${c.version}`} title={`Approved knowledge reference ${c.id}`}><Icon name="book" size={12} />{c.title} · v{c.version}</span>)}</div>}{message.role === 'assistant' && <div className="message-mode">{message.mode === 'openrouter' ? 'Generated with OpenRouter' : 'Local support workflow'}</div>}</article>;
}
