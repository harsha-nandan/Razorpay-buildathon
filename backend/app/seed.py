from sqlalchemy.orm import Session

from . import auth
from .demo_history import seed_demo_history
from .models import Customer, Product, Seller

PRODUCTS = [
    dict(
        sku="EARBUDS-01",
        title="Pulse Wireless Earbuds",
        description="Active-noise-cancelling true wireless earbuds, 30h battery with case.",
        category="audio",
        price_paise=249900,
        image_url="https://images.example.com/pulse-earbuds.jpg",
        tags=["audio", "wireless", "bestseller"],
        complements=["CASE-EARBUDS-01", "POWERBANK-01"],
    ),
    dict(
        sku="CASE-EARBUDS-01",
        title="Silicone Case for Pulse Earbuds",
        description="Shock-absorbing silicone case with carabiner clip.",
        category="accessories",
        price_paise=39900,
        image_url="https://images.example.com/earbuds-case.jpg",
        tags=["accessory", "protection"],
        complements=[],
    ),
    dict(
        sku="SPEAKER-01",
        title="Orbit Bluetooth Speaker",
        description="360-degree sound, IPX7 waterproof, 12h battery.",
        category="audio",
        price_paise=349900,
        image_url="https://images.example.com/orbit-speaker.jpg",
        tags=["audio", "outdoor"],
        complements=["POWERBANK-01"],
    ),
    dict(
        sku="WATCH-01",
        title="Chrono Smartwatch",
        description="AMOLED display, heart-rate and SpO2 tracking, 7-day battery.",
        category="wearables",
        price_paise=449900,
        image_url="https://images.example.com/chrono-watch.jpg",
        tags=["wearable", "fitness", "bestseller"],
        complements=["WATCHBAND-01", "POWERBANK-01"],
    ),
    dict(
        sku="WATCHBAND-01",
        title="Woven Nylon Watch Band",
        description="Breathable nylon strap, fits Chrono Smartwatch.",
        category="accessories",
        price_paise=79900,
        image_url="https://images.example.com/watch-band.jpg",
        tags=["accessory"],
        complements=[],
    ),
    dict(
        sku="POWERBANK-01",
        title="Volt 10000mAh Power Bank",
        description="Slim 20W fast-charge power bank with USB-C.",
        category="power",
        price_paise=179900,
        image_url="https://images.example.com/volt-powerbank.jpg",
        tags=["power", "travel"],
        complements=[],
    ),
    dict(
        sku="SLEEVE-01",
        title="Urban Laptop Sleeve 14-inch",
        description="Water-resistant sleeve with front accessory pocket.",
        category="bags",
        price_paise=129900,
        image_url="https://images.example.com/urban-sleeve.jpg",
        tags=["bag", "work"],
        complements=["POWERBANK-01"],
    ),
    dict(
        sku="KEYBOARD-01",
        title="Type-K Mechanical Keyboard",
        description="Hot-swappable mechanical keyboard, wireless + USB-C.",
        category="peripherals",
        price_paise=549900,
        image_url="https://images.example.com/typek-keyboard.jpg",
        tags=["peripheral", "work", "bestseller"],
        complements=["SLEEVE-01"],
    ),
]

CUSTOMERS = [
    dict(name="Ananya Rao", email="ananya.rao@example.com", phone="+919810000001", segment="vip", lifetime_value_paise=1250000),
    dict(name="Rohit Verma", email="rohit.verma@example.com", phone="+919810000002", segment="repeat", lifetime_value_paise=480000),
    dict(name="Meera Iyer", email="meera.iyer@example.com", phone="+919810000003", segment="repeat", lifetime_value_paise=310000),
    dict(name="Kabir Shah", email="kabir.shah@example.com", phone="+919810000004", segment="new", lifetime_value_paise=0),
    dict(name="Priya Nair", email="priya.nair@example.com", phone="+919810000005", segment="new", lifetime_value_paise=0),
    dict(name="Devansh Gupta", email="devansh.gupta@example.com", phone="+919810000006", segment="lapsed", lifetime_value_paise=195000),
    dict(name="Sara Khan", email="sara.khan@example.com", phone="+919810000007", segment="vip", lifetime_value_paise=980000),
    dict(name="Arjun Menon", email="arjun.menon@example.com", phone="+919810000008", segment="lapsed", lifetime_value_paise=142000),
]


DEMO_CUSTOMER_PASSWORD = "customer123"
DEMO_SELLER_EMAIL = "merchant@pulseandco.test"
DEMO_SELLER_PASSWORD = "merchant123"


def seed(db: Session) -> None:
    if db.query(Product).count() == 0:
        for p in PRODUCTS:
            db.add(Product(**p))
    if db.query(Customer).count() == 0:
        password_hash = auth.hash_password(DEMO_CUSTOMER_PASSWORD)
        for c in CUSTOMERS:
            db.add(Customer(**c, password_hash=password_hash))
    if db.query(Seller).count() == 0:
        db.add(
            Seller(
                name="Pulse & Co. Admin",
                email=DEMO_SELLER_EMAIL,
                password_hash=auth.hash_password(DEMO_SELLER_PASSWORD),
            )
        )
    db.commit()
    seed_demo_history(db)
