# Project charter and scope

Version: v0.1.0  
Baseline date: 2026-10-24 (Asia/Karachi)  
Status: Initial documentation baseline; all application capabilities are **PLANNED**.

## Project purpose

Build an AI Customer Support and Intelligent Ticket Routing System for E-commerce as a reproducible final-year project. Demonstrate how a custom application can answer grounded questions, retrieve authorized order information, perform bounded support workflows, and transfer unresolved conversations to the appropriate staff queue.

The academic question is whether combining an intent classifier with order facts, conversation context, and explicit routing rules improves ticket assignment over keyword routing and classification alone.

## Stakeholders and responsibilities

| Role | Need or responsibility |
| --- | --- |
| Customer | Obtain accurate help and access only their own orders and conversations. |
| Support staff | Review assigned work, see the evidence behind routing, take ownership, and resolve tickets. |
| Administrator | Manage approved knowledge, policy configuration, staff queues, and controlled demo data. |
| Student/developer | Implement, document, test, and evaluate the system with reproducible evidence. |
| Academic evaluator | Inspect design choices, trace requirements to evidence, and reproduce the demonstration. |

No supervisor sign-off, institutional rubric, or project deadline has been supplied. This document does not imply approval by a university or business.

## Initial scope

- A local demo store with synthetic customers, products, stock values, and orders.
- A customer portal with login, order history, and persistent support chat.
- Knowledge retrieval from approved FAQs and policies using local embeddings and PostgreSQL/pgvector.
- Intent classification, deterministic workflow rules, and explainable team routing.
- Owned-order status lookup, cancellation of eligible demo orders, and return-request intake.
- Customer confirmation and duplicate prevention for material changes.
- Staff queues, ticket details, human ownership, conversation replies, and resolution.
- Administrative knowledge and routing configuration with recorded versions.
- An evaluation comparing keyword, classifier-only, and hybrid routing approaches.
- A labeled offline mode so the demonstration remains usable without an available model route.

## Outside the initial scope

- A real checkout, payment gateway, bank transfer, or actual refund processing.
- Carrier integrations, warehouse systems, marketplace integrations, and a production commerce platform.
- WhatsApp, email, voice, image-based damage assessment, and multilingual model evaluation.
- Automated replacements, shipping label purchases, autonomous policy exceptions, and money movement.
- Production hosting, availability guarantees, or unrestricted public registration.

These may become future increments after the core project is evaluated. Simulated shipment events and cancellation/return state changes must be labeled as demo behavior.

## Constraints and assumptions

The application stack, development tools, database, embedding model, and selected generation model must have reviewed open-source licenses. OpenRouter is the sole permitted external hosted model API exception; it is not an open-source component. Only an explicitly allowlisted, verified zero-cost model route may be enabled, with no paid fallback. The system must run locally using existing hardware and require no paid subscription or proprietary container runtime.

Implementation will use React/TypeScript, FastAPI/Python, PostgreSQL/pgvector, local sentence-transformer embeddings, scikit-learn, and an application-owned OpenRouter HTTP adapter. Dependency and model versions will be selected and pinned during implementation after compatibility and license checks. See [technology direction](../architecture/technology-stack.md).

Internet access is needed to obtain dependencies and for optional live generation. Local retrieval, rules, tickets, and deterministic demo responses must remain available after setup when live generation is unavailable. No particular free-model capacity, latency, or continued availability is assumed.

## Completion definition

The final project is complete when the in-scope requirements have implementation and verification evidence, a fresh local setup has been demonstrated, the comparison study has actual reproducible results, unresolved limitations are recorded, and the final documentation baseline is captured. A functioning chat screen alone does not satisfy completion.

## Main risks and planned responses

| Risk | Planned response |
| --- | --- |
| Free model route disappears, changes price, or exhausts quota | Validate route eligibility, bound calls, fail closed, and demonstrate labeled offline fallback. |
| Generated answers invent facts or follow retrieved instructions | Retrieve approved evidence, treat retrieved text as untrusted data, validate actions in code, and test unsupported questions. |
| Access to another customer's order | Derive identity from authentication and enforce ownership on every read and action. |
| Small or repetitive training data inflates results | Keep conversation/paraphrase groups together, reserve a test set, and disclose synthetic data limitations. |
| Scope grows beyond the FYP | Complete one vertical slice at a time and defer out-of-scope channels and integrations. |
| Local hardware cannot serve a large model | Use small local embeddings; generation remains optional and external through the permitted route. |
| Documentation disagrees with implementation | Update requirement links and evidence at each increment; preserve earlier baselines. |

