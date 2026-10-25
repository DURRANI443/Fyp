# Checkout API additions

Predecessor: [v0.2.0 API](../v0.2.0/api-contract.md). All paths below begin with `/api`. Mutations require a customer session cookie and its current `X-CSRF-Token`. Client totals, customer IDs, card credentials, and unknown fields are rejected rather than trusted.

## Quote and confirm

`POST /checkout/quote` takes `{"items":[{"product_id":"...","quantity":1,"size":"M"}]}`. Each cart has 1–20 distinct product/size lines; each quantity is an integer from 1–10. Product sizes and aggregate stock across all sizes are checked against the database.

The result contains `items` with authoritative `price_cents`, `line_total_cents`, name, size, photo metadata, and stock; `subtotal_cents`, `shipping_cents`, `tax_cents`, `total_cents`, `currency`, `simulated:true`, and `quote_token`. Demo shipping/tax are zero; demo currency is USD.

`POST /checkout` takes the same items plus:

```json
{
  "shipping": {
    "name": "Demo Customer",
    "address": "123 Demo Street",
    "city": "Demo City",
    "postal_code": "00000",
    "country": "Demo Country"
  },
  "payment_scenario": "approved",
  "quote_token": "THE_64_CHARACTER_HEX_TOKEN_FROM_QUOTE",
  "idempotency_key": "A_NEW_UUID_FOR_THIS_ATTEMPT"
}
```

The frontend uses this preset fictional address. `payment_scenario` is exactly `approved` or `declined`. A 200 response contains `status`, `simulated:true`, `payment:{reference,status,amount_cents,currency,simulated:true}`, `order` (null after decline), and a human-readable message.

Reusing an idempotency key with its original payload returns the original result. Reusing it with changed content returns 409. A declined simulation is a completed 200 outcome; changing to approval starts a new attempt. An ambiguous network/server failure retries the exact saved request and key. Changed price, insufficient stock, or conflicts return 409 and require an appropriate refresh/review; invalid payload/size returns 422. Unauthenticated requests return 401; wrong role or missing CSRF returns 403. Existing rate limits can return 429.

## Existing resource extensions

- Products add `sku`, `image_url`, and `image_alt`.
- Orders add `shipping_address` and `payment`; item snapshots add `size`, `image_url`, and `returnable_quantity`.
- `GET /system` adds `demo_accounts_enabled`, allowing production login to omit the public demo account chooser.
- Cancelling a checkout-created order restores its reserved stock once and sets its payment to `refunded`, still explicitly simulated. Original seeded orders never reserved stock and therefore do not restock on cancellation.
- The backend stores historical payment/order facts and audit events. It never calls a gateway or accepts card numbers/CVV.
