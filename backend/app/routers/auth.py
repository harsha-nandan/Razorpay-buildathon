from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import auth
from ..db import get_db
from ..models import Customer, Seller
from ..schemas import AuthResponse, CustomerRegisterRequest, LoginRequest, SellerRegisterRequest

router = APIRouter(prefix="/auth", tags=["auth"])


def _customer_profile(c: Customer) -> dict:
    return {"id": c.id, "name": c.name, "email": c.email, "segment": c.segment}


def _seller_profile(s: Seller) -> dict:
    return {"id": s.id, "name": s.name, "email": s.email}


@router.post("/customer/register", response_model=AuthResponse)
def customer_register(req: CustomerRegisterRequest, db: Session = Depends(get_db)):
    if db.query(Customer).filter(Customer.email == req.email).first():
        raise HTTPException(400, "An account with this email already exists.")
    customer = Customer(
        name=req.name,
        email=req.email,
        phone=req.phone,
        password_hash=auth.hash_password(req.password),
        segment="new",
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    token = auth.create_token(customer.id, "customer")
    return AuthResponse(token=token, role="customer", profile=_customer_profile(customer))


@router.post("/customer/login", response_model=AuthResponse)
def customer_login(req: LoginRequest, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.email == req.email).first()
    if not customer or not auth.verify_password(req.password, customer.password_hash):
        raise HTTPException(401, "Incorrect email or password.")
    token = auth.create_token(customer.id, "customer")
    return AuthResponse(token=token, role="customer", profile=_customer_profile(customer))


@router.post("/seller/register", response_model=AuthResponse)
def seller_register(req: SellerRegisterRequest, db: Session = Depends(get_db)):
    if db.query(Seller).filter(Seller.email == req.email).first():
        raise HTTPException(400, "An account with this email already exists.")
    seller = Seller(name=req.name, email=req.email, password_hash=auth.hash_password(req.password))
    db.add(seller)
    db.commit()
    db.refresh(seller)
    token = auth.create_token(seller.id, "seller")
    return AuthResponse(token=token, role="seller", profile=_seller_profile(seller))


@router.post("/seller/login", response_model=AuthResponse)
def seller_login(req: LoginRequest, db: Session = Depends(get_db)):
    seller = db.query(Seller).filter(Seller.email == req.email).first()
    if not seller or not auth.verify_password(req.password, seller.password_hash):
        raise HTTPException(401, "Incorrect email or password.")
    token = auth.create_token(seller.id, "seller")
    return AuthResponse(token=token, role="seller", profile=_seller_profile(seller))


@router.get("/customer/me")
def customer_me(customer: Customer = Depends(auth.get_current_customer)):
    return _customer_profile(customer)


@router.get("/seller/me")
def seller_me(seller: Seller = Depends(auth.get_current_seller)):
    return _seller_profile(seller)
