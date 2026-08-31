from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from ..agents import ai_buyer
from ..config import get_settings
from ..db import get_db
from ..models import Mandate
from ..schemas import AIBuyerRequest

router = APIRouter(prefix="/ai-buyer", tags=["ai-buyer"])


def _x402_quote(result: dict) -> dict:
    """Shapes a payment_required result as an x402-style 402 body - adapted
    to Razorpay payment links rather than x402's usual on-chain settlement,
    since that's this merchant's actual payment rail. Not literal x402/EVM
    wire-format compliance, but the same request/response contract: quote
    first, then present proof of payment to complete."""
    settings = get_settings()
    return {
        "x402Version": 1,
        "error": "payment_required",
        "accepts": [
            {
                "scheme": "razorpay-payment-link",
                "network": "razorpay-live-test-mode" if settings.razorpay_mode == "live" else "razorpay-mock",
                "maxAmountRequired": str(result["amount_paise"]),
                "asset": "INR",
                "resource": "/ai-buyer/purchase",
                "description": "Complete payment at payTo, then retry this request with header "
                "X-PAYMENT: <extra.orderId> as proof of payment.",
                "payTo": result["payment_link"],
                "extra": {"orderId": result["order_id"]},
            }
        ],
        "reply": result["reply"],
        "trace": result["trace"],
    }


@router.post("/purchase")
def purchase(
    req: AIBuyerRequest,
    x_payment: str | None = Header(None, alias="X-PAYMENT"),
    db: Session = Depends(get_db),
):
    """Two-call x402-style handshake:

    1. No X-PAYMENT header: the agent decides what to buy and gets gatekeeper
       approval. If approved, responds 402 Payment Required with a quote
       (amount, payment link, an order reference) instead of completing the
       purchase. Denials/no-match responses come back as normal 200s - there
       was nothing to pay for.
    2. X-PAYMENT header set to the order id from step 1: confirms payment and
       completes the purchase, issuing the invoice.

    mandate_id is optional: a customer-issued spending cap (see /mandates)
    the agent must stay within, checked by the gatekeeper alongside the
    merchant's own policy. Presenting the id is the authorization - the same
    capability-token pattern real agent-payment protocols use instead of a
    full login for the agent itself.
    """
    if x_payment:
        result = ai_buyer.confirm_purchase(db, x_payment)
        if result["status"] == "error":
            return JSONResponse(status_code=404, content=result)
        return result

    mandate = None
    if req.mandate_id:
        mandate = db.get(Mandate, req.mandate_id)
        if not mandate or not mandate.active:
            return JSONResponse(status_code=400, content={"status": "error", "reason": "Unknown or revoked mandate."})

    result = ai_buyer.run_purchase(db, req.intent, req.budget_paise, mandate=mandate)
    if result["status"] == "payment_required":
        return JSONResponse(status_code=402, content=_x402_quote(result))
    return result
