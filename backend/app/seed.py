import logging
import random
from pathlib import Path

from sqlalchemy.orm import Session

from . import auth
from .config import get_settings
from .demo_history import seed_demo_history
from .models import Customer, Product, Seller

logger = logging.getLogger(__name__)

PRODUCT_IMAGES_DIR = Path(__file__).resolve().parent.parent / "product_images"

# Deliberately curated, not randomized - the earbuds-trio decision-quality
# test case (same price, three ratings) needs stable, specific numbers to
# stay meaningful. Every other product gets a randomized rating at seed time.
CURATED_RATINGS: dict[str, tuple[float, int]] = {
    "EARBUDS-01": (4.8, 1200),
    "BOLT-EARBUDS-01": (3.9, 80),
    "ECHO-EARBUDS-01": (4.3, 340),
}


def _random_rating() -> tuple[float, int]:
    return round(random.uniform(3.0, 5.0), 1), random.randint(20, 2000)


def _image_url(sku: str) -> str:
    """Real product photo, served locally from product_images/<SKU>.jpg (see
    main.py's static mount) - no external network/CDN dependency."""
    return f"{get_settings().public_base_url}/static/product_images/{sku}.jpg"


def _warn_missing_product_images() -> None:
    missing = [p["sku"] for p in PRODUCTS if not (PRODUCT_IMAGES_DIR / f"{p['sku']}.jpg").exists()]
    if missing:
        logger.warning(
            "No local product image for SKU(s): %s - add <SKU>.jpg to backend/product_images/",
            ", ".join(missing),
        )


PRODUCTS = [
    dict(
        sku="EARBUDS-01",
        title="FlowState Wireless Earbuds",
        description="Active-noise-cancelling true wireless earbuds, 30h battery with case.",
        category="audio",
        price_paise=249900,
        tags=["audio", "wireless", "bestseller"],
        complements=["CASE-EARBUDS-01", "POWERBANK-01"],
    ),
    dict(
        sku="BOLT-EARBUDS-01",
        title="Bolt Wireless Earbuds",
        description="Budget true wireless earbuds, no ANC, basic bass, 20h battery with case.",
        category="audio",
        price_paise=249900,
        tags=["audio", "wireless"],
        complements=["CASE-EARBUDS-01"],
    ),
    dict(
        sku="ECHO-EARBUDS-01",
        title="Echo Wireless Earbuds",
        description="True wireless earbuds with a strong mic for calls, no ANC, 24h battery with case.",
        category="audio",
        price_paise=249900,
        tags=["audio", "wireless"],
        complements=["CASE-EARBUDS-01"],
    ),
    dict(
        sku="CASE-EARBUDS-01",
        title="Silicone Case for FlowState Earbuds",
        description="Shock-absorbing silicone case with carabiner clip.",
        category="accessories",
        price_paise=39900,
        tags=["accessory", "protection"],
        complements=[],
    ),
    dict(
        sku="SPEAKER-01",
        title="Orbit Bluetooth Speaker",
        description="360-degree sound, IPX7 waterproof, 12h battery.",
        category="audio",
        price_paise=349900,
        tags=["audio", "outdoor"],
        complements=["POWERBANK-01"],
    ),
    dict(
        sku="WATCH-01",
        title="Chrono Smartwatch",
        description="AMOLED display, heart-rate and SpO2 tracking, 7-day battery.",
        category="wearables",
        price_paise=449900,
        tags=["wearable", "fitness", "bestseller"],
        complements=["WATCHBAND-01", "POWERBANK-01"],
    ),
    dict(
        sku="WATCHBAND-01",
        title="Woven Nylon Watch Band",
        description="Breathable nylon strap, fits Chrono Smartwatch.",
        category="accessories",
        price_paise=79900,
        tags=["accessory"],
        complements=[],
    ),
    dict(
        sku="POWERBANK-01",
        title="Volt 10000mAh Power Bank",
        description="Slim 20W fast-charge power bank with USB-C.",
        category="power",
        price_paise=179900,
        tags=["power", "travel"],
        complements=[],
    ),
    dict(
        sku="SLEEVE-01",
        title="Urban Laptop Sleeve 14-inch",
        description="Water-resistant sleeve with front accessory pocket.",
        category="bags",
        price_paise=129900,
        tags=["bag", "work"],
        complements=["POWERBANK-01"],
    ),
    dict(
        sku="KEYBOARD-01",
        title="Type-K Mechanical Keyboard",
        description="Hot-swappable mechanical keyboard, wireless + USB-C.",
        category="peripherals",
        price_paise=549900,
        tags=["peripheral", "work", "bestseller"],
        complements=["SLEEVE-01"],
    ),
    # --- accessories ---
    dict(
        sku="CABLE-01",
        title="Braided USB-C Cable 2m",
        description="Reinforced nylon-braided USB-C to USB-C cable, 100W PD rated.",
        category="accessories",
        price_paise=59900,
        tags=["accessory", "charging"],
        complements=["POWERBANK-01"],
    ),
    dict(
        sku="MOUNT-01",
        title="Magnetic Phone Mount",
        description="Dashboard/vent magnetic mount, one-hand snap attach.",
        category="accessories",
        price_paise=89900,
        tags=["accessory", "car"],
        complements=[],
    ),
    dict(
        sku="SCREEN-01",
        title="Tempered Glass Screen Protector",
        description="9H hardness, anti-fingerprint coating, bubble-free install kit included.",
        category="accessories",
        price_paise=29900,
        tags=["accessory", "protection"],
        complements=[],
    ),
    # --- wearables ---
    dict(
        sku="BAND-01",
        title="FlowState Fitness Band",
        description="Lightweight fitness band, step/sleep tracking, 10-day battery.",
        category="wearables",
        price_paise=159900,
        tags=["wearable", "fitness"],
        complements=[],
    ),
    dict(
        sku="RING-01",
        title="Aria Smart Ring",
        description="Titanium smart ring, sleep and recovery tracking, 6-day battery.",
        category="wearables",
        price_paise=699900,
        tags=["wearable", "fitness"],
        complements=[],
    ),
    dict(
        sku="WATCH-02",
        title="Trek Rugged Smartwatch",
        description="MIL-STD-810H rugged build, GPS, 14-day battery, built for outdoor use.",
        category="wearables",
        price_paise=549900,
        tags=["wearable", "outdoor", "fitness"],
        complements=["WATCHBAND-01"],
    ),
    # --- power ---
    dict(
        sku="POWERBANK-02",
        title="Volt 20000mAh Power Bank",
        description="High-capacity 20000mAh power bank, dual USB-C PD 30W output.",
        category="power",
        price_paise=259900,
        tags=["power", "travel"],
        complements=["CABLE-01"],
    ),
    dict(
        sku="CHARGER-01",
        title="GaN 65W Wall Charger",
        description="Compact GaN charger, 3-port (2x USB-C + USB-A), laptop-capable.",
        category="power",
        price_paise=169900,
        tags=["power", "charging"],
        complements=["CABLE-01"],
    ),
    dict(
        sku="PAD-01",
        title="Wireless Charging Pad 15W",
        description="Qi-certified 15W fast wireless charging pad, non-slip base.",
        category="power",
        price_paise=139900,
        tags=["power", "charging"],
        complements=[],
    ),
    # --- bags ---
    dict(
        sku="BACKPACK-01",
        title="Commuter Backpack 25L",
        description="Water-resistant commuter backpack, padded 16-inch laptop sleeve, USB-C pass-through port.",
        category="bags",
        price_paise=349900,
        tags=["bag", "work", "travel"],
        complements=["POWERBANK-01"],
    ),
    dict(
        sku="POUCH-01",
        title="Travel Tech Organizer Pouch",
        description="Compact pouch for cables, chargers, and small accessories, water-resistant lining.",
        category="bags",
        price_paise=79900,
        tags=["bag", "travel"],
        complements=["CABLE-01"],
    ),
    dict(
        sku="SLING-01",
        title="Crossbody Gadget Sling",
        description="Slim crossbody sling bag for phone, wallet, and earbuds, adjustable strap.",
        category="bags",
        price_paise=119900,
        tags=["bag", "everyday"],
        complements=[],
    ),
    # --- peripherals ---
    dict(
        sku="MOUSE-01",
        title="Glide Wireless Mouse",
        description="Silent-click wireless mouse, 4000 DPI, USB-C rechargeable.",
        category="peripherals",
        price_paise=129900,
        tags=["peripheral", "work"],
        complements=["KEYBOARD-01"],
    ),
    dict(
        sku="HEADSET-01",
        title="Focus Noise-Cancelling Headset",
        description="Over-ear headset with active noise cancellation, boom mic, all-day comfort for calls.",
        category="peripherals",
        price_paise=449900,
        tags=["peripheral", "work", "audio"],
        complements=[],
    ),
    dict(
        sku="DOCK-01",
        title="Dual USB-C Dock Hub",
        description="7-in-1 USB-C dock: HDMI, dual USB-A, SD/microSD, 100W passthrough charging.",
        category="peripherals",
        price_paise=259900,
        tags=["peripheral", "work"],
        complements=["KEYBOARD-01", "MOUSE-01"],
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
DEMO_SELLER_EMAIL = "merchant@flowstate.test"
DEMO_SELLER_PASSWORD = "merchant123"


def seed(db: Session) -> None:
    _warn_missing_product_images()
    if db.query(Product).count() == 0:
        for p in PRODUCTS:
            rating, review_count = CURATED_RATINGS.get(p["sku"]) or _random_rating()
            db.add(Product(**p, image_url=_image_url(p["sku"]), rating=rating, review_count=review_count))
    if db.query(Customer).count() == 0:
        password_hash = auth.hash_password(DEMO_CUSTOMER_PASSWORD)
        for c in CUSTOMERS:
            db.add(Customer(**c, password_hash=password_hash))
    if db.query(Seller).count() == 0:
        db.add(
            Seller(
                name="FlowState Admin",
                email=DEMO_SELLER_EMAIL,
                password_hash=auth.hash_password(DEMO_SELLER_PASSWORD),
            )
        )
    db.commit()
    seed_demo_history(db)
