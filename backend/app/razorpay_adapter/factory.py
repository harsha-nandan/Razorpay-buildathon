from functools import lru_cache

from ..config import get_settings
from .interface import RazorpayGateway
from .mock_gateway import MockGateway


@lru_cache
def get_gateway() -> RazorpayGateway:
    settings = get_settings()
    if settings.razorpay_mode.lower() == "live":
        from .live_gateway import LiveGateway

        return LiveGateway()
    return MockGateway()
