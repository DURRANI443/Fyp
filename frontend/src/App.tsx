import { useCallback, useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { api, ApiError, errorText, notifySessionChange, post, SESSION_CHANGE_KEY, setSession } from './api';
import type { Session, System, User } from './types';
import { Badge, ErrorBox, Icon, Loading } from './ui';
import { Orders, Shop, Support } from './customer';
import { Inbox, Insights, KnowledgeBase, Team } from './staff';
import { Cart, useCart } from './store';

export function Login({ onLogin, system }: { onLogin: (session: Session) => void; system: System | null }) {
  const demoAccounts = system?.demo_accounts_enabled !== false;
  const [account, setAccount] = useState('customer');
  const [email, setEmail] = useState(demoAccounts ? 'customer@demo.local' : '');
  const [password, setPassword] = useState(demoAccounts ? 'DemoPass123!' : '');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => { if (!demoAccounts) { setEmail(''); setPassword(''); } }, [demoAccounts]);
  const login = async (event: FormEvent) => {
    event.preventDefault(); setBusy(true); setError('');
    try { const result = await post<Session>('/auth/login', { email, password }); onLogin(result); }
    catch (e) { setError(errorText(e)); } finally { setBusy(false); }
  };
  return <div className="login-page"><section className="login-story"><a className="brand" href="#"><span className="brand-mark"><Icon name="spark" size={26} /></span>northstar<span className="brand-period">.</span></a><div className="login-story-copy"><div className="eyebrow">GOOD SUPPORT STARTS HERE</div><h1>A little help.<br />A better everyday.</h1><p>Thoughtful essentials, clear answers, and real people when you need them.</p><div className="login-illustration"><div className="illustration-orbit orbit-one" /><div className="illustration-orbit orbit-two" /><div className="illustration-spark"><Icon name="spark" size={85} /></div><div className="floating-note note-one"><span className="note-icon"><Icon name="box" /></span><div><strong>Where’s my order?</strong><span>Let’s take a look together.</span></div></div><div className="floating-note note-two"><span className="note-icon"><Icon name="check" /></span><div><strong>A little less worry.</strong><span>You’re in the right place.</span></div></div></div></div><div className="login-story-footer"><span>SHOP WELL. FEEL SUPPORTED.</span><span>EST. 2026</span></div></section><main className="login-main"><div className="login-topline"><span>YOUR EVERYDAY, SIMPLIFIED</span><Badge>Demo workspace</Badge></div><div className="login-form-wrap"><div className="eyebrow">MAKE YOURSELF AT HOME</div><h2>Welcome to Northstar.</h2><p className="login-subtitle">{demoAccounts ? 'Choose a demo account to explore the experience.' : 'Sign in with the account provided by your administrator.'}</p>{demoAccounts && <div className="account-options" role="group" aria-label="Demo account"><button className={account === 'customer' ? 'selected' : ''} onClick={() => { setAccount('customer'); setEmail('customer@demo.local'); setPassword('DemoPass123!'); }}><Icon name="shop" /><strong>Customer</strong><span>Shop & get help</span></button><button className={account === 'support' ? 'selected' : ''} onClick={() => { setAccount('support'); setEmail('support@demo.local'); setPassword('DemoPass123!'); }}><Icon name="chat" /><strong>Support</strong><span>Care for customers</span></button><button className={account === 'admin' ? 'selected' : ''} onClick={() => { setAccount('admin'); setEmail('admin@demo.local'); setPassword('DemoPass123!'); }}><Icon name="shield" /><strong>Admin</strong><span>Manage the workspace</span></button></div>}<form className="form-stack" onSubmit={login}><label>Email address<input autoComplete="username" type="email" required value={email} onChange={e => setEmail(e.target.value)} /></label><label>Password<input autoComplete="current-password" type="password" required value={password} onChange={e => setPassword(e.target.value)} /></label><ErrorBox message={error} /><button className="button login-submit" disabled={busy}>{busy ? 'Opening your workspace…' : 'Enter workspace'}<Icon name="arrow" size={18} /></button></form><div className="demo-note"><Icon name="shield" size={18} /><span>This workspace uses synthetic demo data. No real purchases or payments take place.</span></div></div><footer className="login-footer"><span>Northstar · Customer care, thoughtfully built.</span><span className="connection-state"><i />{system ? system.llm_mode === 'openrouter' && system.llm_configured ? 'OpenRouter configured' : 'Local demo mode' : 'Connecting to local server'}</span></footer></main></div>;
}

type Tab = 'shop' | 'cart' | 'orders' | 'support' | 'inbox' | 'knowledge' | 'team' | 'insights';
function Workspace({ user, system, logout }: { user: User; system: System | null; logout: () => Promise<void> }) {
  const [tab, setTab] = useState<Tab>(user.role === 'customer' ? 'shop' : 'inbox');
  const [initialMessage, setInitialMessage] = useState<string | null>(null);
  const [supportKey, setSupportKey] = useState(0);
  const [error, setError] = useState('');
  const [loggingOut, setLoggingOut] = useState(false);
  const customer = user.role === 'customer';
  const cart = useCart(user.id);
  const cartCount = cart.lines.reduce((sum, line) => sum + line.quantity, 0);
  const nav: { id: Tab; name: string; icon: string }[] = customer ? [{ id: 'shop', name: 'The collection', icon: 'shop' }, { id: 'cart', name: `Cart (${cartCount})`, icon: 'shop' }, { id: 'orders', name: 'My orders', icon: 'box' }, { id: 'support', name: 'Get support', icon: 'chat' }] : [{ id: 'inbox', name: 'Support inbox', icon: 'inbox' }, ...(user.role === 'admin' ? [{ id: 'knowledge' as Tab, name: 'Knowledge library', icon: 'book' }, { id: 'team' as Tab, name: 'Team & routing', icon: 'users' }, { id: 'insights' as Tab, name: 'Activity & insights', icon: 'chart' }] : [])];
  const ask = (message = '') => { setInitialMessage(message); setSupportKey(n => n + 1); setTab('support'); };
  const consumeInitial = useCallback(() => setInitialMessage(null), []);
  return <div className="app-shell"><aside className="app-sidebar"><a className="brand" href="#" onClick={e => { e.preventDefault(); setTab(customer ? 'shop' : 'inbox'); }}><span className="brand-mark"><Icon name="spark" size={23} /></span>northstar<span className="brand-period">.</span></a><div className="workspace-label">{customer ? 'THE EVERYDAY STORE' : 'CUSTOMER CARE WORKSPACE'}</div><nav aria-label="Main navigation">{nav.map(item => <button key={item.id} className={tab === item.id ? 'active' : ''} onClick={() => setTab(item.id)} aria-current={tab === item.id ? 'page' : undefined}><Icon name={item.icon} size={20} /><span>{item.name}</span>{tab === item.id && <span className="nav-dot" />}</button>)}</nav><div className="sidebar-bottom">{customer && <div className="sidebar-help"><Icon name="spark" size={24} /><strong>Good help is never far.</strong><p>A question, an order, or just a little guidance.</p><button onClick={() => ask()}>Let’s talk<Icon name="arrow" size={15} /></button></div>}<div className="user-block"><span className="user-avatar">{user.name.split(' ').map(n => n[0]).slice(0, 2).join('')}</span><div><strong>{user.name}</strong><span>{customer ? 'Your personal space' : `${user.role === 'admin' ? 'Administrator' : 'Support specialist'}`}</span></div><button title="Sign out" aria-label="Sign out" className="icon-button" disabled={loggingOut} onClick={async () => { setLoggingOut(true); setError(''); try { await logout(); } catch (e) { setError(errorText(e)); } finally { setLoggingOut(false); } }}><Icon name="logout" size={17} /></button></div></div></aside><div className="app-main"><header className="topbar"><div><span>Northstar</span><span className="breadcrumb-slash">/</span><strong>{nav.find(n => n.id === tab)?.name}</strong></div><div className="topbar-right"><span className="system-status" title={system?.notice ?? 'Loading system status'}><span className="status-dot" />{system ? system.llm_mode === 'openrouter' && system.llm_configured ? 'OpenRouter configured' : 'Local demo mode' : 'Connecting…'}</span><Badge>DEMO STORE</Badge></div></header><main className={`page-content ${tab === 'support' || tab === 'inbox' ? 'conversation-page' : ''}`}><ErrorBox message={error} />{tab === 'shop' && <Shop ask={ask} lines={cart.lines} setLines={cart.setLines} openCart={() => setTab('cart')} />}{tab === 'cart' && <Cart lines={cart.lines} setLines={cart.setLines} userId={user.id} shop={() => setTab('shop')} orders={() => setTab('orders')} />}{tab === 'orders' && <Orders ask={ask} />}{tab === 'support' && <Support key={supportKey} initialMessage={initialMessage} consumeInitial={consumeInitial} />}{tab === 'inbox' && <Inbox user={user} />}{tab === 'knowledge' && <KnowledgeBase />}{tab === 'team' && <Team />}{tab === 'insights' && <Insights />}</main><footer className="app-footer"><span>Thoughtful essentials. Thoughtful support.</span><span>Northstar · Synthetic demo data · {system?.version ?? 'v0.2.0'}</span></footer></div></div>;
}
export default function App() {
  const [session, setCurrentSession] = useState<Session | null>(null);
  const [system, setSystem] = useState<System | null>(null);
  const [loading, setLoading] = useState(true);
  const [connectionError, setConnectionError] = useState('');
  const [retry, setRetry] = useState(0);
  const authRestore = useRef<AbortController | null>(null);
  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    authRestore.current = controller;
    Promise.allSettled([api<Session>('/auth/me', { signal: controller.signal }), api<System>('/system', { signal: controller.signal })]).then(([auth, status]) => {
      if (!active || controller.signal.aborted) return;
      if (auth.status === 'fulfilled') { setSession(auth.value); setCurrentSession(auth.value); }
      else if (!(auth.reason instanceof ApiError && auth.reason.status === 401)) setConnectionError(errorText(auth.reason));
      if (status.status === 'fulfilled') setSystem(status.value);
      setLoading(false);
    });
    return () => { active = false; controller.abort(); };
  }, [retry]);
  useEffect(() => {
    const clear = () => { authRestore.current?.abort(); setSession(null); setCurrentSession(null); setLoading(false); };
    const expired = () => { clear(); notifySessionChange(); };
    const changedInAnotherTab = (event: StorageEvent) => {
      if (event.key !== SESSION_CHANGE_KEY) return;
      clear();
      setConnectionError('Your account changed in another tab. Refresh this workspace to use the current account, or sign in again.');
    };
    window.addEventListener('session-expired', expired);
    window.addEventListener('storage', changedInAnotherTab);
    return () => { window.removeEventListener('session-expired', expired); window.removeEventListener('storage', changedInAnotherTab); };
  }, []);
  const logout = async () => { await post('/auth/logout'); setSession(null); setCurrentSession(null); notifySessionChange(); };
  if (loading) return <div className="app-boot"><div className="brand-mark"><Icon name="spark" size={28} /></div><Loading text="Making room for your everyday…" /></div>;
  return <>{connectionError && <div className="connection-banner"><ErrorBox message={connectionError} retry={() => { setConnectionError(''); setLoading(true); setRetry(n => n + 1); }} /></div>}{session ? <Workspace key={session.user.id} user={session.user} system={system} logout={logout} /> : <Login system={system} onLogin={value => { setSession(value); setCurrentSession(value); setConnectionError(''); notifySessionChange(); }} />}</>;
}
