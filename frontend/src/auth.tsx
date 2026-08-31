import { createContext, useContext, useState, type ReactNode } from "react";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export interface CustomerProfile {
  id: string;
  name: string;
  email: string;
  segment: string;
}

export interface SellerProfile {
  id: string;
  name: string;
  email: string;
}

interface StoredAuth<T> {
  token: string;
  profile: T;
}

function load<T>(key: string): StoredAuth<T> | null {
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as StoredAuth<T>) : null;
  } catch {
    return null;
  }
}

async function authRequest<T>(path: string, body: unknown): Promise<{ token: string; profile: T }> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(detail.detail || `${res.status} ${res.statusText}`);
  }
  const data = await res.json();
  return { token: data.token, profile: data.profile };
}

interface AuthState {
  customer: CustomerProfile | null;
  customerToken: string | null;
  seller: SellerProfile | null;
  sellerToken: string | null;
  loginCustomer: (email: string, password: string) => Promise<void>;
  registerCustomer: (name: string, email: string, password: string) => Promise<void>;
  logoutCustomer: () => void;
  loginSeller: (email: string, password: string) => Promise<void>;
  registerSeller: (name: string, email: string, password: string) => Promise<void>;
  logoutSeller: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

const CUSTOMER_KEY = "pulseco.customerAuth";
const SELLER_KEY = "pulseco.sellerAuth";

export function AuthProvider({ children }: { children: ReactNode }) {
  // Read synchronously on first render (not in a useEffect) - otherwise a
  // full page load/refresh renders route guards with customer=null for one
  // tick before localStorage is read, bouncing a logged-in user to /login.
  const [customer, setCustomer] = useState<CustomerProfile | null>(
    () => load<CustomerProfile>(CUSTOMER_KEY)?.profile ?? null
  );
  const [customerToken, setCustomerToken] = useState<string | null>(
    () => load<CustomerProfile>(CUSTOMER_KEY)?.token ?? null
  );
  const [seller, setSeller] = useState<SellerProfile | null>(() => load<SellerProfile>(SELLER_KEY)?.profile ?? null);
  const [sellerToken, setSellerToken] = useState<string | null>(() => load<SellerProfile>(SELLER_KEY)?.token ?? null);

  async function loginCustomer(email: string, password: string) {
    const { token, profile } = await authRequest<CustomerProfile>("/auth/customer/login", { email, password });
    localStorage.setItem(CUSTOMER_KEY, JSON.stringify({ token, profile }));
    setCustomerToken(token);
    setCustomer(profile);
  }

  async function registerCustomer(name: string, email: string, password: string) {
    const { token, profile } = await authRequest<CustomerProfile>("/auth/customer/register", {
      name,
      email,
      password,
    });
    localStorage.setItem(CUSTOMER_KEY, JSON.stringify({ token, profile }));
    setCustomerToken(token);
    setCustomer(profile);
  }

  function logoutCustomer() {
    localStorage.removeItem(CUSTOMER_KEY);
    setCustomerToken(null);
    setCustomer(null);
  }

  async function loginSeller(email: string, password: string) {
    const { token, profile } = await authRequest<SellerProfile>("/auth/seller/login", { email, password });
    localStorage.setItem(SELLER_KEY, JSON.stringify({ token, profile }));
    setSellerToken(token);
    setSeller(profile);
  }

  async function registerSeller(name: string, email: string, password: string) {
    const { token, profile } = await authRequest<SellerProfile>("/auth/seller/register", { name, email, password });
    localStorage.setItem(SELLER_KEY, JSON.stringify({ token, profile }));
    setSellerToken(token);
    setSeller(profile);
  }

  function logoutSeller() {
    localStorage.removeItem(SELLER_KEY);
    setSellerToken(null);
    setSeller(null);
  }

  return (
    <AuthContext.Provider
      value={{
        customer,
        customerToken,
        seller,
        sellerToken,
        loginCustomer,
        registerCustomer,
        logoutCustomer,
        loginSeller,
        registerSeller,
        logoutSeller,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
