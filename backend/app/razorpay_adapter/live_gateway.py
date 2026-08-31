from typing import Any

import razorpay

from ..config import get_settings
from .interface import RazorpayGateway


class LiveGateway(RazorpayGateway):
    """Talks to the real Razorpay test-mode API via the official SDK."""

    def __init__(self) -> None:
        settings = get_settings()
        if not (settings.razorpay_key_id and settings.razorpay_key_secret):
            raise RuntimeError(
                "RAZORPAY_MODE=live but RAZORPAY_KEY_ID/RAZORPAY_KEY_SECRET are not set in backend/.env"
            )
        self.client = razorpay.Client(auth=(settings.razorpay_key_id, settings.razorpay_key_secret))

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
        payload: dict[str, Any] = {
            "amount": amount_paise,
            "currency": currency,
            "description": description,
            "notes": notes or {},
        }
        if customer_name or customer_email or customer_contact:
            payload["customer"] = {
                "name": customer_name,
                "email": customer_email,
                "contact": customer_contact,
            }
            payload["notify"] = {"sms": bool(customer_contact), "email": bool(customer_email)}
        return self.client.payment_link.create(payload)

    def fetch_payment_link(self, payment_link_id: str) -> dict[str, Any]:
        return self.client.payment_link.fetch(payment_link_id)

    def simulate_payment(self, payment_link_id: str, outcome: str) -> dict[str, Any]:
        # Real payments can't be forced from the server side - this just
        # reports the true current status so the UI can show what actually
        # happened after a human pays (or doesn't) via the short_url.
        return self.fetch_payment_link(payment_link_id)
