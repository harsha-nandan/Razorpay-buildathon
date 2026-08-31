from sqlalchemy.orm import Session

from ..models import CartSession


def get_cart(db: Session, session_id: str) -> list[dict]:
    row = db.get(CartSession, session_id)
    return list(row.items) if row else []


def save_cart(db: Session, session_id: str, items: list[dict]) -> None:
    row = db.get(CartSession, session_id)
    if row is None:
        row = CartSession(session_id=session_id, items=items)
        db.add(row)
    else:
        row.items = items
    db.commit()


def cart_total_paise(items: list[dict]) -> int:
    return sum(item["price_paise"] * item["quantity"] for item in items)


def clear_cart(db: Session, session_id: str) -> None:
    save_cart(db, session_id, [])
