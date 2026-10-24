# Implemented system diagrams

Version: v0.2.0  
Date: 2026-10-24, Asia/Karachi

| Diagram | Editable source | SVG export |
| --- | --- | --- |
| Local application architecture and optional model boundary | [architecture.mmd](architecture.mmd) | [architecture.svg](architecture.svg) |
| Support, confirmation and human-ownership flow | [support-flow.mmd](support-flow.mmd) | [support-flow.svg](support-flow.svg) |
| Actual schema: key fields and foreign-key relationships | [data-model.mmd](data-model.mmd) | [data-model.svg](data-model.svg) |

These diagrams describe the v0.2.0 implementation. They replace no file in the captured v0.1.0 baseline. The architecture identifies optional configured PostgreSQL and cached embedding support; diagram inclusion does not assert a successful installation or live model call. The verification record states which paths were exercised.

The ER diagram omits cosmetic product/item color and icon columns for readability. Composite unique constraints are `(conversation_id, client_message_id)` on messages, `(user_id, key)` on idempotency records, and `(key, version)` on knowledge documents. A ticket has a unique conversation ID. Nullable sender, assignee, actor, proposal-item and proposal-conversation references are shown as optional relationships. Teams and conversation context are JSON fields, not separate entities. Knowledge documents are independent versioned records; citation IDs are retained in message metadata.

Re-render for comparison with `npm run docs:render -- v0.2.0 .local/diagram-check/v0.2.0` using the project-pinned Mermaid CLI and an installed Chromium executable. The comparison output stays outside the immutable captured baseline. Renderer output and inspection evidence are linked in [verification](../verification.md). No diagram depicts a real checkout, payment processor, refund operation or pgvector index.
