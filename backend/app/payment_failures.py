"""Realistic payment-decline reasons for the mock gateway, modeled on the
kinds of codes Razorpay's actual payment failure webhooks surface. Every
failed transaction gets a specific code, a plain-language reason, and a
concrete remedy - never just "payment failed"."""

from dataclasses import dataclass


@dataclass(frozen=True)
class FailureDetail:
    code: str
    reason: str
    remedy: str


FAILURE_CATALOG: dict[str, FailureDetail] = {
    "insufficient_funds": FailureDetail(
        code="insufficient_funds",
        reason="The issuing bank declined the payment because the account/card didn't have sufficient funds.",
        remedy="Try a different card or UPI account, or add funds and retry the same payment link.",
    ),
    "card_declined_by_issuer": FailureDetail(
        code="card_declined_by_issuer",
        reason="The card issuer declined this transaction without a specific reason - often a bank-side risk block.",
        remedy="Contact your bank to authorize online/international payments, or pay with a different card.",
    ),
    "expired_card": FailureDetail(
        code="expired_card",
        reason="The card used for this payment has expired.",
        remedy="Retry with a valid, non-expired card.",
    ),
    "incorrect_otp": FailureDetail(
        code="incorrect_otp",
        reason="The one-time password entered during 3-D Secure authentication was incorrect or expired.",
        remedy="Retry the payment and enter the OTP sent to your registered mobile number within the time limit.",
    ),
    "bank_server_error": FailureDetail(
        code="bank_server_error",
        reason="The issuing bank's server didn't respond in time to authorize the payment.",
        remedy="This is usually temporary - wait a minute and retry the same payment link.",
    ),
}

DEFAULT_FAILURE_CODE = "card_declined_by_issuer"


def get_failure_detail(code: str | None) -> FailureDetail:
    return FAILURE_CATALOG.get(code or "", FAILURE_CATALOG[DEFAULT_FAILURE_CODE])
