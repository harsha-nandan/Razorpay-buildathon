import time
import uuid
from typing import Any

from .interface import RazorpayGateway


class MockGateway(RazorpayGateway):
    """Deterministic stand-in for the Razorpay test-mode API.

    Lets the whole app (agents, gatekeeper, audit trail, UI) run end to end
    with zero external keys. Swap RAZORPAY_MODE=live once real test keys are
    available and LiveGateway takes over with the same interface.
    """

    def __init__(self) -> None:
        self._links: dict[str, dict[str, Any]] = {}

    def create_payment_link(
        self,
        *,
        amount_paise: int,
        currency: str,
        description: str,
        customer_name: str = "",
        customer_email: str = "",
        customer_contact: str = "",
        notes: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        link_id = f"plink_mock_{uuid.uuid4().hex[:14]}"
        record = {
            "id": link_id,
            "short_url": f"https://rzp.io/mock/{link_id}",
            "amount": amount_paise,
            "currency": currency,
            "description": description,
            "status": "created",
            "customer": {
                "name": customer_name,
                "email": customer_email,
                "contact": customer_contact,
            },
            "notes": notes or {},
            "created_at": int(time.time()),
        }
        self._links[link_id] = record
        return dict(record)

    def fetch_payment_link(self, payment_link_id: str) -> dict[str, Any]:
        record = self._links.get(payment_link_id)
        if not record:
            raise KeyError(f"Unknown mock payment link '{payment_link_id}'")
        return dict(record)

    def simulate_payment(self, payment_link_id: str, outcome: str) -> dict[str, Any]:
        record = self._links.get(payment_link_id)
        if not record:
            raise KeyError(f"Unknown mock payment link '{payment_link_id}'")
        if outcome not in ("paid", "failed"):
            raise ValueError("outcome must be 'paid' or 'failed'")
        record["status"] = outcome
        record["payment_id"] = f"pay_mock_{uuid.uuid4().hex[:14]}" if outcome == "paid" else ""
        return dict(record)
