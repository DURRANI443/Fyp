# Implementation contract — v0.2.0

Date: 2026-10-24. User priorities: working solo, deliver a local MVP today, default appearance, English, OpenRouter key to be supplied later. This version consolidates several original planned increments into a demonstrable MVP; achieved scope and remaining work are recorded in the implementation and verification documents.

## Transport

JSON API under `/api`; session cookie `support_session`, HTTP-only, same-site lax. Login and `GET /auth/me` return `{user, csrf_token}`. All authenticated writes send `X-CSRF-Token`. Frontend uses same-origin requests through the Vite proxy or backend-served built assets. Error body is FastAPI `{detail: string}`. IDs are opaque strings; timestamps ISO 8601 UTC; money in integer minor units and a currency string. Demo currency is USD.

## Shared DTOs

- User: `{id, name, email, role: customer|support|admin, teams: string[], available: boolean}`.
- Product: `{id, name, category, description, price_cents, currency, color, icon, stock, sizes: string[]}`.
- Order: `{id, number, customer_id, status: processing|shipped|delivered|cancelled, shipping_status, tracking_number, created_at, delivered_at, total_cents, currency, version, items: [{id, product_id, name, quantity, price_cents, color, icon}], returns: [{id,item_id,quantity,status,reason}], timeline: [{label,at,complete}], can_cancel, can_return}`.
- Message: `{id, role: user|assistant|staff|system, content, mode: local|openrouter|system, created_at, citations: [{id,title,version}], intent?, sender_name?}`.
- Proposal: `{id, kind: cancel_order|create_return_request, order_id, order_number, item_id?, quantity?, reason, status: pending|executed|expired, expires_at, summary, result?}`.
- Ticket: `{id, conversation_id, customer_name, subject, team, priority: normal|high, status: queued|assigned|in_progress|waiting_customer|resolved, assignee_id?, assignee_name?, summary, routing_reason, created_at, updated_at}`.
- Conversation summary: `{id, title, mode: assistant|handoff_pending|human_owned|closed, updated_at, preview}`.
- Conversation detail: summary fields plus `{messages: Message[], ticket: Ticket|null, proposals: Proposal[]}`.
- Knowledge: `{id, key, title, content, category, version, approved, created_at}`.

## API routes

Root-owned foundation routes:

- `GET /health` → `{status, version, database}`; `GET /system` → `{version, llm_mode, llm_configured, model, knowledge_mode, notice}`.
- `POST /auth/login {email,password}` → `{user,csrf_token}`; `GET /auth/me` same; `POST /auth/logout` → `{ok:true}`.
- `GET /products` → Product[]; `GET /orders` → Order[]; `GET /orders/{id}` → Order.
- `GET /admin/knowledge` → Knowledge[]; `POST /admin/knowledge {key,title,content,category,approved}` → Knowledge; `PATCH /admin/knowledge/{id} {approved}` → Knowledge.
- `GET /admin/users` → User[]; `PATCH /admin/users/{id} {teams?,available?}` → User.
- `GET /admin/audit` → array of `{id,event_type,actor_name,details,created_at}`; `GET /admin/metrics` → `{counts,by_team,by_intent,model_mode}`.
- `GET /policies` → `{return_window_days,confirmation_minutes,cancellation_rule}`.

Support-agent-owned routes:

- `GET /conversations` → Conversation summary[]; `POST /conversations {title?}` → detail.
- `GET /conversations/{id}` → detail; `POST /conversations/{id}/messages {content,client_message_id}` → detail.
- `POST /conversations/{id}/handoff` → detail.
- `POST /action-proposals {kind,order_id,item_id?,quantity?,reason?,conversation_id?}` → Proposal.
- `POST /action-proposals/{id}/confirm {idempotency_key}` → `{proposal: Proposal, order: Order, receipt: string}`.
- `GET /staff/tickets` → Ticket[]; `GET /staff/tickets/{id}` → `{ticket,conversation,order?:Order}`.
- `POST /staff/tickets/{id}/claim` → Ticket; `POST /staff/tickets/{id}/messages {content}` → detail.
- `POST /staff/tickets/{id}/resolve {outcome,return_to_assistant:boolean}` → Ticket.
- `POST /staff/returns/{id}/review {status: approved|rejected}` → `{id,status}`.

## Python integration contracts

Root provides `app.db.get_db`, `app.models` ORM classes, `app.auth.current_user` and `app.auth.require_staff` / `require_admin`; unsafe-request CSRF enforcement happens in current_user. Root provides `app.serializers.user_dict/product_dict/order_dict`, and `app.services.audit.record_event(db, actor_id, event_type, details)` without committing.

Shared models (all string UUID primary keys; Python aware UTC datetimes normalized by serializers): User(name,email,password_hash,role,teams JSON,available); SessionToken(user_id,token_hash,csrf_token,expires_at); Product(name,category,description,price_cents,currency,color,icon,stock,sizes JSON); Order(number,customer_id,status,shipping_status,tracking_number,created_at,delivered_at,total_cents,currency,version,items relationship); OrderItem(order_id,product_id,name,quantity,price_cents,color,icon); Conversation(customer_id,title,mode,context JSON,created_at,updated_at); Message(conversation_id,sender_id nullable,role,content,mode,meta JSON,client_message_id nullable,created_at); Ticket(conversation_id unique,team,priority,status,assignee_id nullable,summary,routing_reason,created_at,updated_at); Proposal(user_id,conversation_id nullable,order_id,kind,item_id nullable,quantity,reason,status,order_version,policy_version,expires_at,result JSON); ReturnRequest(user_id,order_id,item_id,quantity,reason,status,created_at); IdempotencyRecord(user_id,key,fingerprint,result JSON; unique user+key); KnowledgeDocument(key,title,content,category,version,approved,created_at); AuditEvent(actor_id nullable,event_type,details JSON,created_at). Defaults supplied by root. Message client ID unique per conversation. Team names are logistics/returns/billing/general.

Support agent owns `app/routes/support.py` exposing `router = APIRouter()` with the paths above (no `/api` prefix; root includes it). It may create `app/services/support*.py` and backend support tests.

AI agent owns `app/ai/`, `data/`, and scripts/evaluation helpers under backend. Expose `app.ai.engine.classify(text) -> {intent,confidence,source,intents:list[str]}`; `retrieve(text, documents:list[dict]) -> list[{id,title,version,content,score}]`; async `answer(question,evidence:list[dict],facts:dict|None=None) -> {text:str|None,mode:str,reason:str,model:str|None}`; `status() -> {classifier, retrieval, model}`. Documents use Knowledge DTO fields. Unknowns must not be invented; support service owns deterministic wording/actions. Generation reads root settings via `app.config.settings` (llm_mode,openrouter_api_key,openrouter_model,openrouter_base_url,openrouter_timeout_seconds,openrouter_max_output_tokens). AI modules must work without importing DB and without a key/network by default.

Demo accounts: customer@demo.local, other@demo.local, support@demo.local, admin@demo.local. Shared demo-only password `DemoPass123!`. Local/synthetic data only. Support operator is a member of all four queues so the solo student can demonstrate handoff. No real checkout or payments.
