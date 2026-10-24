# Testing and academic evaluation strategy

Version: v0.1.0  
Baseline date: 2026-10-24 (Asia/Karachi)  
Status: Proposed method only. Application tests, experiments, metrics, and live API checks are **NOT RUN**.

## Verification layers

| Layer | Planned tools | Focus |
| --- | --- | --- |
| Backend unit tests | pytest | Policy boundaries, intent/rule logic, confirmation expiry, request validation, adapter limits |
| Database/API integration | pytest with isolated PostgreSQL/pgvector | Roles, ownership, migrations, transactions, retries, query filters, retrieval provenance |
| UI behavior | Vitest and React Testing Library | Clarification, confirmation, source references, state labels, errors, staff controls |
| End-to-end | Playwright | Customer lookup, grounded question, confirmed cancellation, return intake, human handoff |
| Manual review | Recorded checklist and screenshots where useful | Keyboard access, clarity, setup reproduction, handoff-summary quality |
| Comparative experiment | Versioned Python evaluation scripts | Routing baselines, held-out metrics, answer/workflow quality, timing, failures |

Default tests must run offline with synthetic data, deterministic generation fixtures, and no real API key. Optional live OpenRouter checks are separate, explicit, and permitted only after model license and zero-cost eligibility checks. Passing fixture-based tests does not demonstrate live-model quality.

## High-value behavioral cases

- A customer requests another customer's order or conversation.
- A support user attempts to change an admin policy.
- A prompt or knowledge chunk tells the assistant to ignore authorization or issue a refund.
- An order becomes ineligible between preview and confirmed execution.
- A confirmation expires or is reused for another order/action.
- A request is retried, submitted concurrently, or reuses an idempotency key with different content.
- A policy boundary falls exactly on the selected return-window cutoff.
- Two staff members claim the same ticket; only one obtains ownership.
- The customer sends another message while awaiting or receiving human support.
- Model metadata is missing, nonzero-priced, or outside the allowlist; the adapter refuses the call.
- Generation times out or quota is exhausted; a usable labeled fallback appears.
- An active knowledge document is replaced or withdrawn; new answers use only approved content.

Use a real isolated PostgreSQL test database for behavior involving pgvector, transactions, or concurrency; an in-memory substitute would not establish those properties.

## Routing comparison design

Compare three implementations on the same held-out scenarios:

1. **Keyword baseline:** documented keyword rules and a general-support fallback.
2. **Classifier baseline:** local trained classifier using a fixed feature pipeline, mapped to teams without contextual workflow rules.
3. **Hybrid router:** the same classifier combined with conversation context, verified order facts, queue availability, and explicit rule precedence.

Freeze label definitions and decision rules before inspecting test outcomes. Intent labels and routing labels are separate: a cancellation intent may route to logistics or general support depending on order state. Include single-intent, mixed-intent, ambiguous, out-of-scope, and explicit-human-request cases. Store expected outstanding tasks for mixed requests rather than forcing every conversation into one intent label.

## Dataset and split policy

Create a documented synthetic dataset with conversation IDs, paraphrase-family/group IDs, scenario facts, intent labels, destination-team labels, and label rationale. Do not present synthetic customer messages as real support traffic.

- Start with a proposed grouped 70/15/15 train/validation/test split, adjusting only if class/group sizes require it and documenting the reason before evaluation.
- Keep complete conversations and closely related paraphrases in the same partition.
- Apply feature fitting, vocabulary building, and training only to the training partition.
- Tune model settings and fallback thresholds on validation data only.
- Freeze the test partition and record dataset hashes before final comparison.
- Report sample count and class balance; do not claim statistical strength from a small set.
- Keep routing-policy edge cases and adversarial security scenarios visible even when they are not representative of normal traffic.

No dataset count, trained model, performance value, or split file exists in this documentation baseline.

## Measures and interpretation

| Measure | Planned method |
| --- | --- |
| Intent performance | Per-class precision/recall/F1, macro-F1, support counts, and confusion matrix; report mixed-intent task retention separately. |
| Routing correctness | Correct expected queue over eligible scenarios, plus accuracy by intent/scenario and correct fallback behavior. |
| Grounded-answer quality | Review whether each factual claim is supported, references match the claim, the answer resolves the question, and abstention is appropriate. |
| Retrieval quality | Record whether the required approved document appears in the top-k results; freeze k before final measurement. |
| Workflow success | Correct final state and response over eligible end-to-end tasks, with failure reasons. |
| Safety/integrity | Unauthorized reads/actions, unsupported state claims, duplicate material actions, and unpaused bot replies; report counts even if zero. |
| Handoff quality | Check request, verified facts, attempted actions, unresolved needs, and routing reason against a fixed rubric. |
| Latency | p50/p95 with hardware, warm/cold conditions, concurrency, and sample count; separate local API, retrieval, and external generation. |

Use the same test scenarios across routing methods and report paired differences. If the sample supports it, use grouped bootstrap intervals by conversation for routing metrics; otherwise present descriptive results and disclose uncertainty. If only one human annotator is available, state that limitation rather than claiming inter-rater agreement.

There is no promised macro-F1 or claim that the hybrid method will win. Unexpected or negative results are valid findings. The proposed local performance target in NFR-007 is an engineering target, not a measured result and not a promise about free external inference.

## Reproducibility record

Each experiment report must include the code revision, runtime and dependency versions, operating system/hardware, dataset version and hashes, split/seed, classifier settings, routing-rule version, prompt version, knowledge version, model ID and eligibility-check time when live generation is used, run command, timestamps, raw outputs, and analysis method. Redact keys and unnecessary identifiers.

Store later evidence under the corresponding versioned baseline, for example `doc/v0.6.0/verification/`, with machine-readable result artifacts alongside their explanation. Record actual failures and skipped cases. Test IDs from [the traceability matrix](../requirements/traceability-matrix.md) must link to evidence and actual test code in that future baseline.

## Release decision

Before the final demonstration, verify all core functional scenarios, role/ownership boundaries, action confirmation, duplicate prevention, and human-ownership behavior. Any unresolved defect that permits unauthorized access, unintended action, or paid generation blocks live demonstration of the affected capability. Document other limitations and demonstrate the verified subset honestly.

The final release also needs clean-setup evidence and a completed comparison report. Documentation review can validate this baseline's consistency, but cannot substitute for application tests or experimental results.

