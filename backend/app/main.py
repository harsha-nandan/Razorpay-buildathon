from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .db import SessionLocal, init_db
from .routers import ai_buyer, audit, auth, campaigns, cart, catalog, chat, invoices, mandates, orders, stats
from .seed import seed

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="Agentic Commerce for Razorpay Merchants",
    description="Grows a merchant's revenue and makes them transactable by an AI buyer, "
    "on Razorpay test-mode APIs, with every money action bounded and gated.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(catalog.router)
app.include_router(chat.router)
app.include_router(cart.router)
app.include_router(campaigns.router)
app.include_router(ai_buyer.router)
app.include_router(audit.router)
app.include_router(orders.router)
app.include_router(invoices.router)
app.include_router(mandates.router)
app.include_router(stats.router)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "llm_provider": settings.llm_provider,
        "razorpay_mode": settings.razorpay_mode,
    }
