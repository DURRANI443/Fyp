# AI implementation design

Version: v0.2.0 | Date: 2026-10-24 (Asia/Karachi)

The application uses local intent classification and approved-document retrieval. Optional OpenRouter generation explains retrieved policies. Identity, permissions, order state, action confirmation and ticket ownership remain in backend services; the language model receives no tools and cannot change orders.

## Public interface

`backend/app/ai/engine.py` exposes:

- `classify(text)` returns primary intent, an uncalibrated classifier score, the decision source and a mixed-intent list.
- `retrieve(text, documents)` returns up to three relevant approved documents with ID, title, version, content and score.
- `await answer(question, evidence, facts=None)` returns text only when generation passes its checks. Otherwise it returns `text=None`, `mode=local` and a reason for the support service's deterministic fallback.
- `status()` reports the classifier, actual retrieval mode and configured hosted model, if enabled.
- `warmup()` trains the small local classifier and loads/exercises the optional cached embedding model without network access. The normal application startup calls it in a worker thread before reporting readiness.

The modules do not import the database. Offline mode and a missing API key cause no model-service request. Unit tests use HTTPX MockTransport and no real key.

## Intent classification and routing

The local scikit-learn pipeline fits only the 144 fixed training examples in `data/intents/v1/dataset.json`. It combines word TF-IDF n-grams (1–2) with character-within-word TF-IDF n-grams (3–5), weighted 1.0 and 0.55. Logistic regression uses C=6.0, balanced class weights, maximum 1,000 iterations and random seed 42. The model is trained locally on first use; no untrusted pickle or hosted classifier is loaded.

Nine labels are supported: tracking, return, cancel, product, policy, damage, billing, human and unknown. A confidence threshold of 0.22 was selected using validation macro-F1 only. It is not a calibrated certainty or an authorization threshold.

The hybrid stage applies explicit intent patterns, distinguishes general policy questions from action requests, and handles simple cancellation/return negation. Mixed messages retain multiple intents. Priority is human, damage, billing, cancel, return, tracking, product, policy. The support service combines this result with conversation context and real order facts. For a new request it independently treats classifier-only predictions below 0.35 as unknown; explicit rules and valid workflow continuation are handled separately. That service guard is not included in the standalone classifier benchmark. The service remains responsible for final routing and confirmations.

This classifier is a demonstration model. Its small synthetic corpus has weak rejection of unfamiliar questions, and rules handle only simple negation. See the measured errors in [AI evaluation](ai-evaluation.md). High confidence or a rule match never bypasses order ownership or eligibility checks.

## Retrieval and local model artifacts

The selected embedding model is `sentence-transformers/all-MiniLM-L6-v2`, pinned to revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`. Its model card declares Apache-2.0. [Model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)

The explicit setup script downloads model artifacts into `.local/model-cache/all-MiniLM-L6-v2`; this is a file download, not hosted inference. Runtime loading uses CPU, `local_files_only=True` and `trust_remote_code=False`. Runtime never downloads a missing model. If the package/model is unavailable, retrieval uses a clearly reported local TF-IDF fallback. Restart the backend after downloading the model because failed loading is cached in the process.

Local CPU loading and retrieval were executed successfully in this milestone. The standalone smoke's initial cold query included 60.5 seconds of import/model initialization; warm queries in the fixture took approximately 16–44 milliseconds. The normal application startup warms these local models before readiness so this cost is paid during visible startup rather than the first customer policy request. Missing/failed optional embeddings select TF-IDF fallback. Startup may therefore take a minute on this workstation; these are observed timings, not a latency guarantee. See [the artifact record](evidence/embedding-model.json) and [evaluation](ai-evaluation.md).

Only approved documents are candidates. For a repeated document key, the highest approved version is used; a new unapproved draft does not hide the existing approved policy. The admin service must deactivate prior approvals when approving a replacement. Matches retain source IDs and versions. Sentence-transformer retrieval uses normalized cosine similarity with a 0.30 cutoff; TF-IDF uses a 0.08 cutoff. These cutoffs are initial engineering choices, not validated production thresholds. Embedding vectors are cached in process for this small corpus; this module does not claim a persisted pgvector index.

## Free-only OpenRouter adapter

The only reviewed route is `google/gemma-4-31b-it:free`. Google's model card declares Apache-2.0; this is an open-weight model license, not a claim that all training data and infrastructure are open source. OpenRouter itself is the permitted external hosted-service exception. [Google model card](https://huggingface.co/google/gemma-4-31B-it)

The public catalog was inspected on 2026-10-24. It reported explicit zero prompt and completion prices for the selected route and omitted the optional per-request price. The implementation does **not** treat absence as confirmed zero: it requires zero prompt/completion prices, rejects every returned nonzero or malformed pricing dimension, and always requests a zero per-request price ceiling. OpenRouter documents per-request caps under `provider.max_price.request`. [Catalog](https://openrouter.ai/api/v1/models), [provider price caps](https://openrouter.ai/docs/guides/routing/provider-selection#max-price)

Before every inference, the adapter retrieves fresh model metadata and checks the reviewed ID, required price fields and support for `max_tokens` and `response_format`. It rejects a different API origin; the key can be sent only to `https://openrouter.ai/api/v1/chat/completions`. Requests specify:

- One exact reviewed `:free` model, no fallback model list, tools, web-search plugins or retries.
- Provider `allow_fallbacks=false`, `require_parameters=true`, `data_collection=deny` and zero prompt/completion/request price ceilings.
- At most two concurrent generations, a whole-call timeout capped at 45 seconds, and at most 768 output tokens (default configuration may be lower).
- A question capped at 3,000 characters and three evidence excerpts capped at 2,200 characters each.

Privacy preferences may leave no eligible free provider. Quota exhaustion, provider rejection, timeout, malformed output and failed price checks produce local fallback. The client never relaxes privacy or price restrictions to make a request succeed. Free-service availability and upstream privacy behavior remain external dependencies. [Provider routing and data policies](https://openrouter.ai/docs/guides/routing/provider-selection)

## Grounding, privacy and limitations

Prompt version `grounded-policy-v1` requests JSON with `answer` and `source_ids`. IDs must refer to supplied evidence. The adapter rejects missing citations, unsupported digit-based numeric claims, URLs/email addresses, recognized action-completion claims, unexpected tool calls, unexpected models and nonzero reported usage cost. Only a small allowlist of fact keys is accepted. Email addresses, API-key-like strings, UUIDs, long numbers, recognized order references and explicitly introduced names/addresses are redacted from outbound content. Full customer/order records are not sent.

These are defense layers, not a proof of semantic faithfulness or complete personal-data removal. Natural-language claims, spelled-out numbers and novel identifying text are not comprehensively verified. The application therefore keeps order-specific responses and all actions deterministic, uses synthetic demo data, retains sources, and needs independent live-answer review before broader use.

Logs record configured model ID, prompt version, document versions, elapsed time and outcome. They do not log credentials or prompt text. Deterministic replies are marked `local`; they are never described as successful hosted generations.

## Reproduction

From the project root with the documented virtual environment installed:

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests/test_ai.py -q
.\.venv\Scripts\python.exe backend/scripts/evaluate.py --output .local/intent-evaluation.json
.\.venv\Scripts\python.exe backend/scripts/ai_download_model.py
.\.venv\Scripts\python.exe backend/scripts/ai_smoke.py --output .local/ai-smoke-local.json
```

The download is an explicit network/setup operation. Classification, retrieval and tests thereafter need no hosted model API. The separate optional command below sends only a synthetic return-policy question, reads the local ignored API key, performs all free-route checks and prints status/outcome/model without printing the key or generated answer:

```powershell
.\.venv\Scripts\python.exe backend/scripts/ai_smoke.py --live
```

Live generation has not been verified in this milestone until a real key is supplied and that command produces recorded success. The command exits with status 2 if the key is absent or the guarded request fails.
