"""Idempotent reference data. Prices and stock are synthetic demonstration values."""
from sqlalchemy import select

from app.models import KnowledgeDocument, Product


# These are ordinary physical products, not live supplier inventory. Photography
# is illustrative; the application has no affiliation with a manufacturer.
CATALOG = [
    dict(sku="NS-TEE-001", name="Everyday Cotton Tee", category="Essentials",
         description="A soft 100% cotton crew-neck tee with a relaxed fit. Machine wash cold.",
         price_cents=2400, color="sage", icon="shirt", sizes=["S", "M", "L", "XL"]),
    dict(sku="NS-TOTE-001", name="Weekend Canvas Tote", category="Accessories",
         description="A sturdy cotton-canvas carryall with an inside pocket. 16 litre capacity.",
         price_cents=3200, color="sand", icon="bag", sizes=["One size"]),
    dict(sku="NS-KNIT-001", name="Cloud Knit Sweater", category="Knitwear",
         description="A warm cotton-blend knit with ribbed cuffs and an easy everyday fit.",
         price_cents=6800, color="cream", icon="sweater", sizes=["S", "M", "L", "XL"]),
    dict(sku="NS-SHIRT-001", name="Everyday Linen Shirt", category="Essentials",
         description="A breathable linen-blend button-down with a relaxed fit and chest pocket.",
         price_cents=5400, color="blue", icon="shirt", sizes=["S", "M", "L", "XL"]),
    dict(sku="NS-CAP-001", name="Trail Cap", category="Accessories",
         description="An adjustable cotton cap with a curved brim. Fits head circumferences 54–60 cm.",
         price_cents=2200, color="olive", icon="cap", sizes=["Adjustable"]),
    dict(sku="NS-SCARF-001", name="Soft Ribbed Scarf", category="Knitwear",
         description="A soft recycled-polyester scarf, 180 by 30 cm. Hand wash cool.",
         price_cents=3600, color="rose", icon="scarf", sizes=["One size"]),
    dict(sku="NS-PACK-001", name="Everyday Travel Backpack", category="Accessories",
         description="A 20 litre everyday backpack with a padded 15-inch laptop sleeve, front organizer and two bottle pockets. Wipe clean. Demo product specifications.",
         price_cents=5900, color="sand", icon="bag", sizes=["One size"]),
    dict(sku="NS-BOTTLE-001", name="Stainless Steel Water Bottle", category="Lifestyle",
         description="A reusable 750 ml stainless-steel bottle with a screw-top lid. Hand wash only; not microwave safe. Demo product specifications.",
         price_cents=2800, color="sage", icon="bag", sizes=["One size"]),
    dict(sku="NS-SHOES-001", name="Classic Low-Top Sneakers", category="Footwear",
         description="Everyday lace-up sneakers with a canvas upper and rubber sole. US unisex sizing. Spot clean and air dry. Demo product specifications.",
         price_cents=6400, color="cream", icon="bag", sizes=["US 7", "US 8", "US 9", "US 10", "US 11"]),
    dict(sku="NS-AUDIO-001", name="Wireless Over-Ear Headphones", category="Electronics",
         description="Bluetooth over-ear headphones with padded ear cups, a built-in microphone and USB-C charging. Demo specifications; battery life has not been measured.",
         price_cents=7900, color="blue", icon="bag", sizes=["One size"]),
]

PAYMENT_POLICY = (
    "This demonstration store has a simulated checkout. Add products and sizes to the cart, review the current "
    "database price and stock, and choose an approved or declined test payment. No card numbers or payment "
    "security codes are collected. Approved simulations create a demo order and reserve stock; declined "
    "simulations do not create an order. Cancelling an eligible checkout order restores stock and marks its "
    "simulated payment refunded. No actual charge, refund, tax payment, or physical delivery occurs. "
    "Prices, shipping (free), tax (zero), and inventory are demonstration values. Never share card details or passwords in chat."
)

POLICIES = [
    ("returns", "Returns and eligibility", "returns", "You can request a return within 30 days of delivery. Items must be unused and in their original condition. Select the delivered order and item, give a reason, and confirm the request. Staff review the request before providing further instructions. A return request is not a refund. This demonstration does not process real refunds."),
    ("cancellation", "Cancelling an order", "cancellation", "You can cancel an order while its status is processing, before it ships. Review and confirm the cancellation. Shipped or delivered orders cannot be cancelled; eligible delivered items can be submitted for a return. Eligibility is checked again when you confirm. This demo changes only synthetic order data."),
    ("shipping", "Shipping and tracking", "shipping", "Standard shipping normally takes 3–5 business days after dispatch. The current order page shows the latest recorded shipping status. Delivery estimates are not guarantees. If a package is delayed or marked delivered but missing, contact support so the logistics team can review it. Tracking numbers in this demonstration are simulated."),
    ("sizing", "Finding your size", "sizing", "Our clothing comes in S, M, L, and XL unless a product states otherwise. Our everyday tees and shirts have a relaxed fit. Choose your usual size for a relaxed look. For a specific measurement or fit question, ask support; do not assume an unavailable measurement."),
    ("care", "Product care", "products", "Wash cotton tees cold with similar colors and air dry where possible. Linen-blend shirts can be washed on a gentle cool cycle. Hand wash the Soft Ribbed Scarf cool. Always follow the item's care label. Product descriptions show known materials and care details."),
    ("payment", "Payment questions", "billing", PAYMENT_POLICY),
    ("damaged", "Damaged or incorrect items", "returns", "If your order has a damaged, incorrect, or missing item, tell support the order reference, affected item, and what happened. The returns team reviews replacement and return options. A report does not automatically approve a replacement or refund."),
    ("support", "Getting help from a person", "support", "You can ask for a human at any time or select Talk to a person. Your conversation and a summary go to the appropriate team. The assistant pauses while your ticket waits or a staff member responds. Actual queue status is shown; a response time is not guaranteed in this demo."),
]


def ensure_catalog(db):
    products = []
    for row in CATALOG:
        product = db.scalar(select(Product).where(Product.sku == row["sku"]))
        if product is None:
            product = db.scalar(select(Product).where(Product.name == row["name"]))
        if product is None:
            product = Product(**row, stock=30, currency="USD")
            db.add(product)
        elif product.sku is None:
            product.sku = row["sku"]
        # Do not reset prices, stock, descriptions or any existing order history.
        if not product.image_url:
            product.image_url = f"/products/{row['sku'].lower()}.jpg"
        if not product.image_alt:
            product.image_alt = f"Illustrative photograph for {row['name']}"
        products.append(product)
    db.flush()
    return products


def ensure_knowledge(db):
    for key, title, category, content in POLICIES:
        latest = db.scalar(select(KnowledgeDocument).where(KnowledgeDocument.key == key)
                           .order_by(KnowledgeDocument.version.desc()).limit(1))
        if latest is None:
            db.add(KnowledgeDocument(key=key, title=title, category=category, content=content, approved=True))
        elif key == "payment" and latest.version == 1 and "No checkout, card collection" in latest.content:
            # Only upgrade the obsolete original fixture, retaining its history.
            # An administrator's subsequent policy versions are left untouched.
            approved = latest.approved
            latest.approved = False
            db.add(KnowledgeDocument(key=key, title=title, category=category, content=content,
                                     version=2, approved=approved))


def seed_reference_data(db):
    ensure_catalog(db)
    ensure_knowledge(db)
    db.commit()


def main():
    from app.db import SessionLocal
    with SessionLocal() as db:
        seed_reference_data(db)
    print("Reference catalog and policies ready. Existing inventory and customer data preserved; no demo accounts created.")


if __name__ == "__main__":
    main()
