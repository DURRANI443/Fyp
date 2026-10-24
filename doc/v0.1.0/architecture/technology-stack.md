# Technology stack, licenses, and cost boundaries

Version: v0.1.0 | Date: 2026-10-24 | Status: selected design direction; application not implemented

## Decision

Use a locally runnable modular application with an open-source frontend, backend, database, retrieval pipeline, classifier, and test tools. OpenRouter is the user-approved exception for hosted generation. No hosted workflow engine or paid service is required.

The stack is selected for a student project: one backend, one frontend, one relational database, and a clear evaluation path. Add infrastructure only when a demonstrated need justifies it.

## Component selection

| Area | Technology | Purpose and rationale | License/source |
| --- | --- | --- | --- |
| UI | React | Customer chat, order views, and staff/admin dashboard | [MIT](https://github.com/facebook/react/blob/main/LICENSE) |
| Frontend language | TypeScript | Typed request/response contracts and UI state | [Apache-2.0](https://github.com/microsoft/TypeScript/blob/main/LICENSE.txt) |
| Frontend tooling | Vite | Local development and static production build | [MIT](https://github.com/vitejs/vite/blob/main/LICENSE) |
| Styling | Plain CSS | Responsive layouts without a commercial design system | Project-authored, MIT |
| API | FastAPI | Python endpoints, request validation, and OpenAPI documentation | [MIT](https://github.com/fastapi/fastapi/blob/master/LICENSE), [features](https://fastapi.tiangolo.com/features/) |
| Validation | Pydantic | Validate input, configuration, and structured model output | [MIT](https://github.com/pydantic/pydantic/blob/main/LICENSE) |
| Persistence | SQLAlchemy and Alembic | Database transactions and versioned migrations | [SQLAlchemy MIT](https://github.com/sqlalchemy/sqlalchemy/blob/main/LICENSE), [Alembic MIT](https://github.com/sqlalchemy/alembic/blob/main/LICENSE) |
| Database | PostgreSQL | Customers, orders, tickets, permissions, and audit history | [PostgreSQL License](https://www.postgresql.org/about/licence/) |
| Vector search | pgvector | Search local knowledge embeddings in the same database | [PostgreSQL License](https://github.com/pgvector/pgvector/blob/master/LICENSE) |
| Embeddings | Sentence Transformers | Generate vectors locally; no hosted embedding API | [Apache-2.0](https://github.com/huggingface/sentence-transformers/blob/main/LICENSE) |
| Initial embedding model | `sentence-transformers/all-MiniLM-L6-v2` | Compact English text embeddings; evaluate retrieval on store policies | [Apache-2.0 model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) |
| Intent model | scikit-learn TF-IDF + logistic regression | Trainable and interpretable baseline for intent detection | [BSD-3-Clause](https://github.com/scikit-learn/scikit-learn/blob/main/COPYING) |
| Model HTTP adapter | HTTPX | A small backend-only OpenRouter client with timeout/error handling | [BSD-3-Clause](https://github.com/encode/httpx/blob/master/LICENSE.md) |
| Backend testing | pytest | Policy, authorization, workflow, and model-adapter tests | [MIT](https://github.com/pytest-dev/pytest/blob/main/LICENSE) |
| Frontend testing | Vitest + React Testing Library | UI behavior and accessible interactions | [Vitest MIT](https://github.com/vitest-dev/vitest/blob/main/LICENSE.md), [Testing Library MIT](https://github.com/testing-library/react-testing-library/blob/main/LICENSE) |
| End-to-end testing | Playwright | Browser journeys across customer and staff interfaces | [Apache-2.0](https://github.com/microsoft/playwright/blob/main/LICENSE) |
| Diagrams | Mermaid / Mermaid CLI | Editable text diagrams and reproducible SVG exports | [Mermaid MIT](https://github.com/mermaid-js/mermaid/blob/develop/LICENSE), [CLI MIT](https://github.com/mermaid-js/mermaid-cli/blob/master/LICENSE) |
| Source history | Git | Local commits and release tags; no hosted account required | [GPL-2.0](https://git-scm.com/about/free-and-open-source) |

These are primary component licenses, not a completed transitive dependency audit. Capture exact versions, model revisions, and a dependency/license inventory during implementation. Each dependency keeps its own license; this project's MIT license does not relicense dependencies or model artifacts.

## Runtime targets and observed workstation

- Frontend/document tooling target: Node.js 24 LTS. Node v24.14.1 and npm 11.11.0 were found locally.
- Backend target: Python 3.13, with a clean virtual environment and compatible pinned ML wheels verified during v0.2.0. The workstation lists Python 3.13 and 3.14; bare `python` currently resolves to 3.14. Do not assume bare `python` creates the intended application environment.
- PostgreSQL and pgvector must be installed/configured during application setup. A working database service was not verified in this documentation baseline.
- A container runtime is optional. Native services are acceptable; Podman is the preferred open-source container option if needed. Docker Desktop is not a project prerequisite.
- Internet is needed initially to obtain packages/model files, and for live OpenRouter generation. Cached local retrieval and deterministic workflows should remain usable without live inference.
- A dedicated GPU is not a baseline requirement. CPU embedding performance and available memory must be measured on the project machine before fixing latency targets.

## OpenRouter free inference

OpenRouter is an external hosted service, not an open-source part of the application. The honest project description is: **open-source application and local infrastructure, with OpenRouter as the permitted free hosted inference service**.

As checked on 2026-10-24, the no-credit-purchase free allowance is 20 requests/minute and 50 requests/day. Failed requests also count. A larger advertised allowance requires purchasing credits and is excluded from this project's zero-purchase baseline. These limits may change; see [pricing](https://openrouter.ai/pricing) and [limits](https://openrouter.ai/docs/api_reference/limits).

The initial candidate is `google/gemma-4-31b-it:free`: it appeared with zero prompt/completion prices in the [public model catalog](https://openrouter.ai/api/v1/models), and Google's [model card](https://huggingface.co/google/gemma-4-31B-it) declares Apache-2.0. This is a candidate for evaluation, not a guarantee of availability, quality, or an already-working integration. Describe it as an Apache-2.0-licensed open-weight model; do not claim that all training data and training infrastructure are open source.

Before enabling it, implement:

1. An explicit reviewed model/license allowlist and fresh zero-price checks. Reject missing, paid, or unreviewed routes.
2. A backend-only API key. Default to `LLM_MODE=offline` until local configuration is supplied.
3. A fixed model ID rather than `openrouter/free`, which selects among different available models and weakens licensing control and reproducibility. See [free router behavior](https://openrouter.ai/docs/guides/routing/routers/free-router).
4. No paid fallback model, plugin, search tool, or credit purchase. Apply zero prompt/completion/request price ceilings where the selected free route supports them; fail gracefully if constraints cannot be honored. Provider fallback is distinct from model fallback. See [provider routing](https://openrouter.ai/docs/guides/routing/provider-selection).
5. Request/token bounds, limited retries with backoff, timeout handling, and a useful fallback on quota exhaustion. Unit and integration tests use a local stub and consume no quota.
6. Synthetic inputs and minimal identifiers in prompts. Keep logging/training opt-ins disabled and review upstream provider policies; do not assume a free tier offers contractual privacy controls. See [data collection](https://openrouter.ai/docs/guides/privacy/data-collection) and [provider policies](https://openrouter.ai/docs/guides/privacy/provider-logging).

The system must not pretend a local canned response was generated by the hosted model. Offline mode can return matching policy excerpts, actual local order status, and create support tickets with an explicit generation-unavailable indicator.

## Cost assumptions

| Item | Required payment | Qualification |
| --- | --- | --- |
| Project code and selected OSS libraries | None | Preserve relevant license notices |
| Local PostgreSQL and knowledge search | None | Uses the existing computer's resources |
| Local embedding/classification | None | Initial artifact download; no hosted inference charge |
| OpenRouter free route | None under the selected free allowance | Quotas, availability, and terms are external dependencies |
| Local demo hosting | None for software/service subscription | Existing hardware, electricity, and connectivity are assumed |
| Public hosting, domain, email/SMS, WhatsApp | Not required | Outside initial scope; no promise of permanent free public hosting |

## Academic distinction

Train and evaluate the small intent classifier on a versioned, labeled dataset. Use pretrained embeddings for retrieval and a pretrained hosted model for wording grounded in retrieved facts. The project does not train a foundation language model. The main engineering/evaluation contribution is the integrated workflow and comparison of keyword, classifier, and hybrid routing approaches.

Start with English text support. Urdu, Roman Urdu, voice, and damage-image assessment are extensions that require their own dataset/model and evaluation decisions.
