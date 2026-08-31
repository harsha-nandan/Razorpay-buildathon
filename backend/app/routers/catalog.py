"""Agent-readable catalog: a machine-consumable product feed + discovery
manifest, in the spirit of the emerging agentic-commerce protocols (ACP,
AP2, x402) - so an external AI shopping agent can discover this merchant,
understand its policies, and know exactly which endpoint transacts.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..models import Product

router = APIRouter(tags=["catalog"])


def _product_payload(p: Product) -> dict:
    return {
        "id": p.sku,
        "title": p.title,
        "description": p.description,
        "category": p.category,
        "price": {"amount": p.price_paise, "currency": p.currency, "display": f"₹{p.price_paise / 100:,.2f}"},
        "availability": "in_stock" if p.in_stock else "out_of_stock",
        "image_url": p.image_url,
        "tags": p.tags,
        "complements": p.complements,
    }


@router.get("/catalog")
def list_catalog(db: Session = Depends(get_db)):
    products = db.query(Product).all()
    return {"merchant": "Pulse & Co. Electronics Accessories", "currency": "INR", "products": [_product_payload(p) for p in products]}


@router.get("/catalog/{sku}")
def get_catalog_item(sku: str, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.sku == sku).first()
    if not product:
        return {"error": "not_found"}
    return _product_payload(product)


@router.get("/.well-known/agentic-commerce.json")
def agentic_commerce_manifest():
    """A minimal machine-readable manifest describing how an AI agent can
    transact with this merchant end to end - the "agent-readable catalog +
    AI buyer" surface. Not a full ACP/AP2 implementation, but the same idea:
    self-describing capabilities, policies, and a single transact endpoint.
    """
    settings = get_settings()
    return {
        "merchant": {
            "name": "Pulse & Co. Electronics Accessories",
            "currency": "INR",
            "environment": "razorpay_test_mode" if settings.razorpay_mode == "mock" else "razorpay_test_mode_live_api",
        },
        "catalog_url": "/catalog",
        "transact": {
            "protocol": "conversational-tool-use",
            "endpoint": "/ai-buyer/purchase",
            "method": "POST",
            "schema": {"intent": "string, natural-language description of what to buy", "budget_paise": "integer|null"},
            "description": "POST a natural-language purchase intent and optional budget; the merchant's "
            "own checkout agent will search its catalog, build a cart, and attempt checkout, gated by its "
            "own risk policy on every step.",
        },
        "policies": {
            "max_single_order_inr": settings.max_single_order_paise / 100,
            "max_discount_percent": settings.max_discount_percent,
            "currency": "INR",
            "payment_rails": ["razorpay_payment_links"],
        },
        "audit": {
            "endpoint": "/audit",
            "description": "Every money-moving decision this merchant's agents make - allowed or denied, "
            "and why - is readable here for verification.",
        },
    }
