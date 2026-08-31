from abc import ABC, abstractmethod
from typing import Any


class RazorpayGateway(ABC):
    """Everything that touches money goes through this interface.

    Two implementations exist: a MockGateway (default, no keys required, safe
    to run in a hackathon demo) and a LiveGateway (real Razorpay test-mode
    API). The rest of the app never knows which one it's talking to.
    """

    @abstractmethod
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
        """Create a payment link. Returns dict with id, short_url, status, amount."""

    @abstractmethod
    def fetch_payment_link(self, payment_link_id: str) -> dict[str, Any]:
        """Fetch current status of a payment link."""

    @abstractmethod
    def simulate_payment(self, payment_link_id: str, outcome: str) -> dict[str, Any]:
        """Move a payment link to a terminal state for demo purposes.

        outcome: "paid" | "failed". In live mode this cannot programmatically
        force a real payment, so it just re-fetches the true status and
        raises if the caller asked for something that hasn't happened.
        """
