const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit, token?: string | null): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${API_BASE}${path}`, { headers, ...options });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail || `${res.status} ${res.statusText}`);
  }
  return res.json();
}

export interface Product {
  sku?: string;
  id?: string;
  title: string;
  description: string;
  category: string;
  price_paise?: number;
  price?: { amount: number; currency: string; display: string };
  in_stock?: boolean;
  availability?: string;
  tags: string[];
}

export interface TraceItem {
  type: "text" | "tool_call" | "tool_result";
  role: string;
  text?: string;
  tool?: string;
  input?: unknown;
  output?: string;
  status?: string;
}

export interface ChatResponse {
  session_id: string;
  reply: string;
  trace: TraceItem[];
  cart: { sku: string; title: string; price_paise: number; quantity: number }[];
}

export interface AIBuyerResponse {
  session_id: string;
  reply: string;
  trace: TraceItem[];
}

export interface AuditEntry {
  id: string;
  timestamp: string;
  correlation_id: string;
  actor: string;
  action_type: string;
  description: string;
  amount_paise: number;
  decision: "allow" | "deny" | "n/a";
  decided_by: string;
  reasoning: string;
  policy_refs: string[];
  before_state: Record<string, unknown>;
  after_state: Record<string, unknown>;
}

export interface Campaign {
  id: string;
  name: string;
  goal: string;
  discount_percent: number;
  target_segment: string;
  product_sku: string;
  budget_paise: number;
  max_recipients: number;
  status: string;
  message_copy: string;
  reasoning: string;
  spent_paise: number;
  created_at: string;
  recipients_reached: number;
  actions?: { customer_name: string; amount_paise: number; payment_link_url: string; status: string }[];
}

export interface Order {
  id: string;
  session_id: string;
  source: string;
  amount_paise: number;
  currency: string;
  status: string;
  items: { sku: string; title: string; price_paise: number; quantity: number }[];
  payment_link_url: string;
  failure_code: string;
  failure_reason: string;
  failure_remedy: string;
  created_at: string;
  simulated?: boolean;
  real_gateway_status?: string | null;
}

export const FAILURE_SCENARIOS: { code: string; label: string }[] = [
  { code: "insufficient_funds", label: "Insufficient funds" },
  { code: "card_declined_by_issuer", label: "Declined by issuer" },
  { code: "expired_card", label: "Expired card" },
  { code: "incorrect_otp", label: "Incorrect OTP" },
  { code: "bank_server_error", label: "Bank server timeout" },
];

export interface Invoice {
  id: string;
  order_id: string;
  invoice_number: string;
  subtotal_paise: number;
  tax_paise: number;
  total_paise: number;
  currency: string;
  customer_name: string;
  customer_email: string;
  items: { sku: string; title: string; price_paise: number; quantity: number }[];
  issued_at: string;
}

export interface DashboardStats {
  total_revenue_paise: number;
  orders_created: number;
  orders_paid: number;
  orders_denied: number;
  orders_failed: number;
  campaigns_total: number;
  campaigns_running_or_completed: number;
  campaigns_denied: number;
  gatekeeper_allows: number;
  gatekeeper_denies: number;
  revenue_by_day: { date: string; revenue_paise: number }[];
  revenue_by_source: { source: string; revenue_paise: number }[];
  funnel: {
    stages: { stage: string; count: number }[];
    by_source: { source: string; attempted: number; approved: number; paid: number }[];
  };
}

export const api = {
  health: () => request<{ status: string; llm_provider: string; razorpay_mode: string }>("/health"),
  catalog: () => request<{ merchant: string; currency: string; products: Product[] }>("/catalog"),

  // Customer-authenticated
  sendChatMessage: (token: string, message: string) =>
    request<ChatResponse>("/chat/message", { method: "POST", body: JSON.stringify({ message }) }, token),
  resetChat: (token: string) => request("/chat/reset", { method: "POST" }, token),
  myOrders: (token: string) => request<Order[]>("/my/orders", undefined, token),
  simulatePayment: (token: string, order_id: string, outcome: "paid" | "failed", failure_code?: string) =>
    request<Order>(
      "/payments/simulate",
      { method: "POST", body: JSON.stringify({ order_id, outcome, failure_code }) },
      token
    ),
  myInvoices: (token: string) => request<Invoice[]>("/invoices/mine", undefined, token),
  invoiceForOrder: (token: string, orderId: string) =>
    request<Invoice>(`/invoices/by-order/${orderId}`, undefined, token),
  removeFromCart: (token: string, sku: string) =>
    request<{ cart: Order["items"]; subtotal_paise: number }>(`/cart/${sku}`, { method: "DELETE" }, token),

  // Public - the agent-facing surface, no login required
  aiBuyerPurchase: (intent: string, budget_paise: number | null) =>
    request<AIBuyerResponse>("/ai-buyer/purchase", { method: "POST", body: JSON.stringify({ intent, budget_paise }) }),

  // Seller-authenticated
  listAudit: (token: string, params?: { actor?: string; decision?: string }) => {
    const qs = new URLSearchParams();
    if (params?.actor) qs.set("actor", params.actor);
    if (params?.decision) qs.set("decision", params.decision);
    const suffix = qs.toString() ? `?${qs}` : "";
    return request<AuditEntry[]>(`/audit${suffix}`, undefined, token);
  },
  listCampaigns: (token: string) => request<Campaign[]>("/campaigns", undefined, token),
  getCampaign: (token: string, id: string) => request<Campaign>(`/campaigns/${id}`, undefined, token),
  createCampaign: (
    token: string,
    body: {
      name: string;
      goal: string;
      discount_percent: number;
      target_segment: string;
      product_sku: string;
      max_recipients: number;
    }
  ) => request<Campaign>("/campaigns", { method: "POST", body: JSON.stringify(body) }, token),
  listOrders: (token: string) => request<Order[]>("/orders", undefined, token),
  listInvoices: (token: string) => request<Invoice[]>("/invoices", undefined, token),
  dashboardStats: (token: string) => request<DashboardStats>("/stats/dashboard", undefined, token),
};

export function formatInr(paise: number): string {
  return `₹${(paise / 100).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}
