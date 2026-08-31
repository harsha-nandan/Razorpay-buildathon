"""Tool factory shared by the checkout agent and the AI-buyer simulator.

Tools are built fresh per request as closures bound to a DB session, a cart
session id, an actor label (who's making the request), and a correlation id
that ties every audit-log row from this turn together. This is the standard
Strands pattern for request-scoped tools - no shared mutable global state.
"""

from typing import Any

from sqlalchemy.orm import Session
from strands import tool

from .. import audit, mandates as mandate_math
from ..gatekeeper.gatekeeper import evaluate as gatekeeper_evaluate
from ..gatekeeper.policy import ProposedAction
from ..models import Mandate, Order, Product
from ..payment_methods import compute_offer, describe as describe_payment_methods
from ..razorpay_adapter.factory import get_gateway
from . import cart as cart_ops
from .search import search_products


def _product_to_dict(p: Product) -> dict[str, Any]:
    return {
        "sku": p.sku,
        "title": p.title,
        "description": p.description,
        "category": p.category,
        "price_paise": p.price_paise,
        "price_inr": round(p.price_paise / 100, 2),
        "in_stock": p.in_stock,
        "tags": p.tags,
    }


def build_checkout_tools(
    db: Session,
    session_id: str,
    correlation_id: str,
    actor: str = "checkout_agent",
    customer_name: str = "",
    customer_email: str = "",
    customer_contact: str = "",
    mandate: Mandate | None = None,
) -> list:
    """Build the tool set a conversational commerce agent needs.

    actor distinguishes who is transacting in the audit trail - a human
    shopper via the checkout_agent, or an external ai_buyer driving the same
    machinery end to end. customer_* is the authenticated shopper's known
    contact info (empty for the anonymous ai_buyer persona) - the agent
    never has to ask for it, it's applied automatically at checkout. mandate,
    when given, is a customer-issued spending authorization the agent is
    bounded by in addition to the merchant's own policy - the agent is never
    told the mandate exists as a tool it can call, it's a silent ceiling.
    """

    @tool
    def search_catalog(query: str = "", category: str = "", max_price_inr: float = 0) -> list[dict]:
        """Search the merchant's catalog by relevance, like a normal shopping-site search box.
        The query is matched against product title, description, category, and tags (with
        plural/singular tolerance), ranked by how many terms hit - not just an exact substring
        match. All filters are optional and combine with AND.

        Args:
            query: Free-text search, e.g. "wireless earbuds" or "something for a home workout".
            category: Exact category filter (e.g. "audio", "wearables", "accessories").
            max_price_inr: Only return products at or below this price in INR (0 = no limit).
        """
        results = search_products(
            db,
            query=query,
            category=category,
            max_price_paise=int(max_price_inr * 100) if max_price_inr else 0,
        )
        return [_product_to_dict(p) for p in results]

    @tool
    def add_to_cart(sku: str, quantity: int = 1) -> dict:
        """Add a product to the shopper's cart by SKU.

        Args:
            sku: The product SKU, as returned by search_catalog.
            quantity: How many units to add (default 1).
        """
        product = db.query(Product).filter(Product.sku == sku).first()
        if not product:
            return {"error": f"No product with SKU '{sku}'."}
        items = cart_ops.get_cart(db, session_id)
        for item in items:
            if item["sku"] == sku:
                item["quantity"] += quantity
                break
        else:
            items.append(
                {
                    "sku": product.sku,
                    "title": product.title,
                    "price_paise": product.price_paise,
                    "quantity": quantity,
                }
            )
        cart_ops.save_cart(db, session_id, items)
        return {"cart": items, "subtotal_paise": cart_ops.cart_total_paise(items)}

    @tool
    def view_cart() -> dict:
        """View the current contents of the shopper's cart and its subtotal."""
        items = cart_ops.get_cart(db, session_id)
        return {"cart": items, "subtotal_paise": cart_ops.cart_total_paise(items)}

    @tool
    def remove_from_cart(sku: str) -> dict:
        """Remove a product from the cart entirely by SKU.

        Args:
            sku: The product SKU to remove.
        """
        items = [i for i in cart_ops.get_cart(db, session_id) if i["sku"] != sku]
        cart_ops.save_cart(db, session_id, items)
        return {"cart": items, "subtotal_paise": cart_ops.cart_total_paise(items)}

    @tool
    def get_upsell_suggestions() -> list[dict]:
        """Suggest complementary add-on products for what's currently in the cart
        (cross-sell/upsell). Call this after items are added, before checkout."""
        items = cart_ops.get_cart(db, session_id)
        in_cart_skus = {i["sku"] for i in items}
        suggested_skus: list[str] = []
        for item in items:
            product = db.query(Product).filter(Product.sku == item["sku"]).first()
            if not product:
                continue
            for complement_sku in product.complements:
                if complement_sku not in in_cart_skus and complement_sku not in suggested_skus:
                    suggested_skus.append(complement_sku)
        suggestions = (
            db.query(Product).filter(Product.sku.in_(suggested_skus), Product.in_stock.is_(True)).all()
            if suggested_skus
            else []
        )
        return [_product_to_dict(p) for p in suggestions]

    @tool
    def check_payment_method(network: str = "") -> list[dict]:
        """Look up whether a card network/payment method is accepted, and its offers,
        EMI eligibility, and the actual price/discount for the shopper's current cart
        (not just a generic "X% off" line) - to answer "which cards do you take?" /
        "do you have EMI on Visa?" / "how much do I save?". Call with no args to list
        everything accepted. NEVER ask the shopper for an actual card number, expiry,
        or CVV here or anywhere else - the Razorpay payment link handles real card
        entry securely on Razorpay's own page, this merchant app never touches raw
        card details.

        Args:
            network: A card network or payment method name (e.g. "Visa", "UPI"). Empty
                returns the full list of accepted methods, their offers, and EMI plans.
        """
        subtotal_paise = cart_ops.cart_total_paise(cart_ops.get_cart(db, session_id))
        results = []
        for m in describe_payment_methods(network):
            results.append(
                {
                    "network": m.network,
                    "accepted": m.accepted,
                    "cart_subtotal_paise": subtotal_paise,
                    "offers": [compute_offer(offer, subtotal_paise) for offer in m.offers],
                    "emi_available": m.emi_available,
                    "emi_min_order_inr": round(m.emi_min_order_paise / 100, 2) if m.emi_available else None,
                    "emi_plans": [
                        {
                            "tenure_months": plan.tenure_months,
                            "interest_rate_percent": plan.interest_rate_percent,
                            "no_cost": plan.interest_rate_percent == 0,
                        }
                        for plan in m.emi_plans
                    ],
                    "notes": m.notes,
                }
            )
        return results

    @tool
    def checkout(discount_percent: int = 0) -> dict:
        """Attempt to check out the current cart: creates a Razorpay payment link
        for the cart total (after an optional discount), but ONLY after the
        gatekeeper approves it against merchant policy. If denied, explain the
        reason to the shopper plainly - do not retry silently. The shopper's
        contact details are already known (they're logged in) - you don't
        need to ask for them.

        Args:
            discount_percent: Discount to apply (0-100), e.g. from an accepted promo. Defaults to 0.
        """
        items = cart_ops.get_cart(db, session_id)
        if not items:
            return {"status": "error", "reason": "Cart is empty - add items before checking out."}

        subtotal_paise = cart_ops.cart_total_paise(items)
        amount_paise = round(subtotal_paise * (1 - discount_percent / 100))
        orders_this_session = db.query(Order).filter(Order.session_id == session_id).count()

        context: dict[str, Any] = {
            "orders_this_session": orders_this_session,
            "discount_percent": discount_percent,
            "skus": [i["sku"] for i in items],
            "subtotal_paise": subtotal_paise,
        }
        if mandate is not None:
            context["mandate_remaining_paise"] = mandate_math.remaining_paise(db, mandate)
            context["mandate_label"] = mandate.label

        action = ProposedAction(
            actor=actor,
            action_type="create_payment_link",
            amount_paise=amount_paise,
            currency="INR",
            description=f"Checkout for {len(items)} item(s), session {session_id}",
            context=context,
        )
        verdict = gatekeeper_evaluate(action)

        if not verdict.allow:
            order = Order(
                session_id=session_id,
                source=actor,
                amount_paise=amount_paise,
                status="denied",
                items=items,
                mandate_id=mandate.id if mandate else None,
            )
            db.add(order)
            db.commit()
            audit.record(
                db,
                action=action,
                verdict=verdict,
                correlation_id=correlation_id,
                before_state={"cart": items},
                after_state={"order_id": order.id, "status": "denied"},
            )
            return {"status": "denied", "reason": verdict.reason, "decided_by": verdict.decided_by}

        gateway = get_gateway()
        link = gateway.create_payment_link(
            amount_paise=amount_paise,
            currency="INR",
            description=action.description,
            customer_name=customer_name,
            customer_email=customer_email,
            customer_contact=customer_contact,
            notes={"session_id": session_id, "actor": actor},
        )
        order = Order(
            session_id=session_id,
            source=actor,
            razorpay_payment_link_id=link["id"],
            razorpay_payment_link_url=link["short_url"],
            amount_paise=amount_paise,
            status="created",
            items=items,
            mandate_id=mandate.id if mandate else None,
        )
        db.add(order)
        db.commit()
        db.refresh(order)
        audit.record(
            db,
            action=action,
            verdict=verdict,
            correlation_id=correlation_id,
            before_state={"cart": items},
            after_state={
                "order_id": order.id,
                "payment_link_id": link["id"],
                "payment_link_url": link["short_url"],
                "status": "created",
            },
        )
        # Cart is intentionally NOT cleared here - only when the payment is
        # confirmed paid. If this payment fails, the shopper can retry
        # checkout on the same cart without rebuilding it from scratch.
        return {
            "status": "approved",
            "order_id": order.id,
            "amount_paise": amount_paise,
            "payment_link": link["short_url"],
            "reason": verdict.reason,
        }

    return [
        search_catalog,
        add_to_cart,
        view_cart,
        remove_from_cart,
        get_upsell_suggestions,
        check_payment_method,
        checkout,
    ]
