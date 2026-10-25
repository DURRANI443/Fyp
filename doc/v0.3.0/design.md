# Design decisions

## Store and checkout

The existing modular monolith remains. Product facts come from the database. Photos illustrate demo merchandise; the catalog does not claim a relationship with a real retailer. Product identifiers, sizes, and quantities form the cart. The backend validates the cart and generates a review token from its current authoritative quote.

Submitting a reviewed cart includes a customer-generated idempotency key. The backend checks authenticated identity, CSRF, the review token, and inventory before committing a simulated payment result. An approved result creates an order and order-item snapshots together with the inventory update. A declined result is still a completed simulation, with no order or inventory reservation. Retrying after an uncertain network response preserves the exact key and payload.

Cart state is scoped to the customer in session storage. Settling an approved payment subtracts only its purchased product/size quantities from the current cart and remembers the completed key. Additions made after submission survive, and simultaneous original/retry responses cannot subtract the same purchase twice. Clearing a saved attempt also checks its key so an old response cannot erase a newer pending request.

Order snapshots retain historical item names and unit prices when catalog descriptions later change. Original seeded orders are distinguished from new inventory-reserving purchases, so cancelling an old fixture cannot incorrectly add stock. Return approval remains a support decision; it does not imply receipt of goods or a real refund.

## Hosting boundaries

The browser uses relative `/api` paths on its Vercel origin. Vercel forwards those paths to the Oracle HTTPS origin. Caddy terminates HTTPS and forwards to a loopback-only FastAPI process. Backend sessions remain opaque HTTP-only cookies with CSRF protection. The exact Vercel origin and API host must be configured; wildcard trusted origins are inappropriate.

The backend alone connects to Supabase PostgreSQL using TLS. The Supabase browser Data API is unnecessary because authentication and ownership checks belong to this application. The deployment guide disables that exposure. PostgreSQL credentials and the OpenRouter key remain on Oracle; the configured Vercel rewrite destination is a public URL, not a secret.

Local SQLite and offline generation remain supported for reproducible demonstration. Live OpenRouter inference remains optional and subject to the existing reviewed free-route checks. Oracle deployment starts with TF-IDF retrieval to keep dependencies and memory practical; local neural retrieval is separately documented in earlier AI evidence.

## Operating limits

This is a single-worker FYP deployment. In-memory rate limiting and retrieval caches are not shared across processes. All money movements are simulated. Free hosting capacity and quotas are external conditions, not guarantees made by this repository. Account provisioning and password changes use a server-side management command; the project does not provide password-reset email or self-service registration.
