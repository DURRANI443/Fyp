# AI evaluation and limitations

Version: v0.2.0 | Date: 2026-10-24 (Asia/Karachi)

## Dataset and protocol

`data/intents/v1/dataset.json` contains **234 AI-assisted synthetic English messages and labels**, authored for this demonstration under the project's MIT license. There are no real customer records and no independent human annotation. Labels were assigned during authoring.

The fixed split contains 144 training, 36 validation and 54 test messages across nine classes. Each class has 16 training, four validation and six test examples. Whole scenario groups remain in one split: four training groups, one validation group and two test groups per class. Examples within each group are related paraphrases or subcases.

The automated audit found no repeated group IDs, exact duplicate messages or cross-split token-set Jaccard similarity of at least 0.70. This detects simple lexical overlap, not semantic leakage. Training and test vocabulary and author style still overlap. The model and routing rules were developed by the same team that authored the dataset.

The learned classifier is trained only on training data. Validation macro-F1 selects the confidence threshold from 0.18, 0.22, 0.26, 0.28, 0.30, 0.34, 0.38 and 0.42; ties favor the higher threshold. The selected value is **0.22**. The held-out test split is not used for fitting or threshold selection. Rules were not revised to remove the observed held-out errors.

## Measured held-out results

The following results come from `backend/scripts/evaluate.py` on 54 test messages. They are observations, not proposed targets.

| Method | Intent accuracy | Macro-F1 | Static mapped-team accuracy |
| --- | ---: | ---: | ---: |
| Keyword baseline | 0.4630 | 0.4650 | 0.7593 |
| TF-IDF + logistic regression | 0.7222 | 0.7003 | 0.8333 |
| Classifier + explicit intent rules | 0.8148 | 0.7865 | 0.9259 |

Mapped-team accuracy applies a fixed mapping: tracking → logistics; return/damage → returns; billing → billing; all other labels → general. It does **not** measure context-aware routing, priority, staff availability, handoff ownership or complete workflow success. Different intent errors can map to the same team.

The [machine-readable report](evidence/intent-evaluation.json) contains the dataset SHA-256, package version, random seed, hyperparameters, validation search, per-class precision/recall/F1, all confusion matrices, every held-out prediction and warm per-message latency. The rerunnable working copy is `.local/intent-evaluation.json`. Raw local latency is workstation-dependent; it is not a production performance claim.

Hybrid per-class results (six held-out examples per class):

| Intent | Precision | Recall | F1 |
| --- | ---: | ---: | ---: |
| Tracking | 0.6667 | 1.0000 | 0.8000 |
| Return | 1.0000 | 0.8333 | 0.9091 |
| Cancel | 0.8571 | 1.0000 | 0.9231 |
| Product | 0.7500 | 0.5000 | 0.6000 |
| Policy | 0.6250 | 0.8333 | 0.7143 |
| Damage | 0.8571 | 1.0000 | 0.9231 |
| Billing | 0.8571 | 1.0000 | 0.9231 |
| Human | 1.0000 | 1.0000 | 1.0000 |
| Unknown | 1.0000 | 0.1667 | 0.2857 |

Hybrid confusion matrix: rows are actual labels; columns are predicted labels. Counts, not percentages:

| Actual / predicted | Track | Return | Cancel | Product | Policy | Damage | Billing | Human | Unknown |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Tracking | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Return | 0 | 5 | 0 | 0 | 0 | 1 | 0 | 0 | 0 |
| Cancel | 0 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 |
| Product | 1 | 0 | 0 | 3 | 2 | 0 | 0 | 0 | 0 |
| Policy | 0 | 0 | 0 | 0 | 5 | 0 | 1 | 0 | 0 |
| Damage | 0 | 0 | 0 | 0 | 0 | 6 | 0 | 0 | 0 |
| Billing | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 0 | 0 |
| Human | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 0 |
| Unknown | 2 | 0 | 1 | 1 | 1 | 0 | 0 | 0 | 1 |

## Observed failures

The hybrid classifier made ten errors in the 54-message test set. Examples include:

- “There is nothing broken … arrange a return” was classified as damage: the rule does not understand that negation.
- A return-policy question mentioning a receipt was classified as billing.
- Product comparisons and occasion-based recommendations were sometimes confused with policy or tracking.
- Several unrelated or ambiguous questions were classified as store intents; unfamiliar-input rejection is weak with this corpus.

The application must use evidence checks, clarification or handoff and must never treat a label as authorization to change an order. A larger independently reviewed dataset, clearer ambiguous-message labels and calibrated rejection thresholds are future evaluation work. Six test examples per class are insufficient for strong reliability claims; no confidence intervals or significance claims are reported.

## Retrieval and generated-answer evaluation

`data/retrieval/v1/cases.json` provides six synthetic policy documents and 13 query checks, including one out-of-domain query. The **TF-IDF fallback passed 13/13 top-1 checks**, and the **local sentence transformer also passed 13/13**, on this small fixture. This is a smoke test authored alongside the implementation, not an independently collected retrieval benchmark. Individual results are retained in the [TF-IDF report](evidence/retrieval-tfidf.json) and [local transformer report](evidence/retrieval-local-transformer.json).

The local model loaded successfully from the pinned artifact cache with Sentence Transformers 6.2.0, Transformers 5.20.2 and Torch 2.14.1+cpu. Actual mode was `local_sentence_transformer`; no hosted embedding inference was used. The first query took **60.5 seconds** on this initial standalone process, including imports/model loading. Subsequent queries took approximately **16–44 milliseconds**. The normal application's startup now warms the local models before reporting readiness; the standalone smoke retains the cold measurement so initialization cost is not hidden behind warm-latency claims. The [artifact record](evidence/embedding-model.json) retains model revision, license, dependency versions and the 90,868,376-byte safetensors SHA-256.

A [second fresh-process run](evidence/retrieval-local-transformer-repeat.json) again passed 13/13 and measured 53.3 seconds on its first query. The difference illustrates why the project reports initialization separately from warm-query latency rather than promising a fixed startup duration.

Live OpenRouter answer quality, citation faithfulness, latency and free-account availability are **NOT MEASURED** because the user has not supplied a key. HTTPX mock tests verify the adapter contract and failure handling, not real model quality. Valid citation IDs and supported digits do not establish that every generated claim is entailed by its source.

The latest executed AI unit-test run passed 30 tests after the approved-version and embedding-failure recovery changes. Coverage includes price metadata and nonzero-cost denial, endpoint/model allowlisting, offline/no-key no-network behavior, privacy redaction, bounded requests, unsupported citations/numbers/actions/links, prompt-injection attempts that cannot change the configured model or create actions, timeout, rate-limit, malformed-response and local-embedding failure fallback. The milestone verification record is the authoritative final suite count.

## Reproduce

```powershell
.\.venv\Scripts\python.exe backend/scripts/evaluate.py --output .local/intent-evaluation.json
.\.venv\Scripts\python.exe -m pytest backend/tests/test_ai.py -q
.\.venv\Scripts\python.exe backend/scripts/ai_smoke.py --output .local/ai-smoke-local.json
```

See [AI design](ai-design.md) for the architecture, licenses, guarded live-smoke command and model-download procedure. See [API contract](api-contract.md) for integration boundaries. Full workflow and authorization checks belong in the milestone verification record separately from this classifier evaluation.
