"""Two separate identities, two separate token scopes.

Customers authenticate to shop via the checkout chat and see their own
orders. Sellers (merchant staff) authenticate to see revenue, campaigns,
and the audit trail. A customer token cannot open seller endpoints and
vice versa - checked by decoding the JWT's "role" claim, not just its
validity.

The catalog, the agentic-commerce manifest, and the AI-buyer endpoint stay
unauthenticated on purpose: those are the public, agent-facing surface an
external AI buyer discovers and transacts against without a human login.
"""

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .config import get_settings
from .db import get_db
from .models import Customer, Seller

_bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    if not password_hash:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_token(subject_id: str, role: str) -> str:
    settings = get_settings()
    payload = {
        "sub": subject_id,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expires_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def _decode(token: str) -> dict:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token") from exc


def get_current_customer(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> Customer:
    if not creds:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sign in as a customer to use this.")
    payload = _decode(creds.credentials)
    if payload.get("role") != "customer":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "A customer login is required for this action.")
    customer = db.get(Customer, payload["sub"])
    if not customer:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Customer account no longer exists.")
    return customer


def get_current_seller(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> Seller:
    if not creds:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sign in as the merchant/seller to use this.")
    payload = _decode(creds.credentials)
    if payload.get("role") != "seller":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "A seller login is required for this action.")
    seller = db.get(Seller, payload["sub"])
    if not seller:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Seller account no longer exists.")
    return seller


def get_current_principal(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> tuple[str, Customer | Seller]:
    """Either a customer or a seller - for endpoints both roles may read,
    like a single invoice, where the handler itself decides who may see what."""
    if not creds:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sign in to use this.")
    payload = _decode(creds.credentials)
    role = payload.get("role")
    if role == "customer":
        principal = db.get(Customer, payload["sub"])
    elif role == "seller":
        principal = db.get(Seller, payload["sub"])
    else:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token role.")
    if not principal:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Account no longer exists.")
    return role, principal
