import { useEffect, useRef, useState } from "react";
import { api, FAILURE_SCENARIOS, formatInr, type CartItem, type Invoice, type TraceItem } from "../api";
import TraceView from "../components/TraceView";
import ProductCard from "../components/ProductCard";
import ProductThumb from "../components/ProductThumb";
import InvoiceView from "../components/InvoiceView";
import TypingIndicator from "../components/TypingIndicator";
import PaymentMethodPanel from "../components/PaymentMethodPanel";
import {
  extractPaymentMethodResult,
  extractSuggestedProducts,
  findLatestCheckoutResult,
  stripMarkdown,
  type PaymentMethodDetail,
  type SuggestedProduct,
} from "../utils";
import { useAuth } from "../auth";
import { useCatalogImages } from "../hooks/useCatalogImages";

interface ChatLine {
  role: "user" | "assistant";
  text: string;
  products?: SuggestedProduct[];
  paymentMethods?: PaymentMethodDetail[];
  trace?: TraceItem[];
}

const STARTER_PROMPTS = [
  "Wireless earbuds under ₹3000",
  "Something for a home workout",
  "What goes well with a smartwatch?",
  "Show me your bestsellers",
];

export default function Chat() {
  const { customer, customerToken } = useAuth();
  const catalogImages = useCatalogImages();
  const [lines, setLines] = useState<ChatLine[]>([]);
  const [input, setInput] = useState("");
  const [cart, setCart] = useState<CartItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [paying, setPaying] = useState(false);
  const [showTrace, setShowTrace] = useState(false);
  const [showCart, setShowCart] = useState(false);
  const [paymentOutcome, setPaymentOutcome] = useState<Record<string, "paid" | "failed">>({});
  const [invoice, setInvoice] = useState<Invoice | null>(null);
  const [failureCode, setFailureCode] = useState(FAILURE_SCENARIOS[0].code);
  const [removingSku, setRemovingSku] = useState<string | null>(null);
  const [resetting, setResetting] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const started = lines.length > 0;
  const cartCount = cart.reduce((n, i) => n + i.quantity, 0);
  const cartTotal = cart.reduce((sum, i) => sum + i.price_paise * i.quantity, 0);
  const lastTrace = lines.length ? lines[lines.length - 1].trace || [] : [];
  const checkoutResult = findLatestCheckoutResult(lastTrace);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [lines, loading]);

  async function cancelAndStartOver() {
    setResetting(true);
    try {
      const res = await api.resetChat(customerToken!);
      setLines([]);
      setInvoice(null);
      setPaymentOutcome({});
      setShowCart(false);
      setShowTrace(false);
      if (res.cancelled_orders > 0) {
        setLines([
          {
            role: "assistant",
            text: `Cancelled ${res.cancelled_orders} unfinished payment attempt${res.cancelled_orders > 1 ? "s" : ""} from before. What are you shopping for today?`,
          },
        ]);
      }
    } finally {
      setResetting(false);
    }
  }

  async function removeItem(sku: string) {
    setRemovingSku(sku);
    try {
      const res = await api.removeFromCart(customerToken!, sku);
      setCart(res.cart);
    } finally {
      setRemovingSku(null);
    }
  }

  async function send(message: string) {
    if (!message.trim() || loading) return;
    setLines((prev) => [...prev, { role: "user", text: message }]);
    setInput("");
    setLoading(true);
    try {
      const res = await api.sendChatMessage(customerToken!, message);
      setLines((prev) => [
        ...prev,
        {
          role: "assistant",
          text: stripMarkdown(res.reply),
          products: extractSuggestedProducts(res.trace),
          paymentMethods: extractPaymentMethodResult(res.trace) ?? undefined,
          trace: res.trace,
        },
      ]);
      setCart(res.cart);
    } catch (e) {
      setLines((prev) => [...prev, { role: "assistant", text: `⚠️ ${String(e)}` }]);
    } finally {
      setLoading(false);
    }
  }

  async function simulatePay(outcome: "paid" | "failed") {
    if (!checkoutResult?.order_id) return;
    const orderId = checkoutResult.order_id;
    setPaying(true);
    try {
      const order = await api.simulatePayment(customerToken!, orderId, outcome, outcome === "failed" ? failureCode : undefined);
      setPaymentOutcome((prev) => ({ ...prev, [orderId]: outcome }));
      const simNote =
        order.simulated && order.real_gateway_status
          ? ` (This is a simulated demo confirmation for the app's UI - the real Razorpay payment link is still "${order.real_gateway_status}" since no card was actually entered.)`
          : "";
      if (outcome === "paid") {
        const inv = await api.invoiceForOrder(customerToken!, orderId);
        setInvoice(inv);
        setLines((prev) => [
          ...prev,
          { role: "assistant", text: `✅ Payment successful! Your invoice is ready below.${simNote}` },
        ]);
      } else {
        setLines((prev) => [
          ...prev,
          {
            role: "assistant",
            text: `❌ Payment declined - ${order.failure_reason}\n\nWhat you can do: ${order.failure_remedy} Your cart is untouched, so just say "try again" and I'll create a fresh payment link.${simNote}`,
          },
        ]);
      }
    } finally {
      setPaying(false);
    }
  }

  if (!started) {
    return (
      <div className="chat-hero">
        <h1>What are you shopping for today, {customer?.name.split(" ")[0]}?</h1>
        <p>Tell me what you need in plain language - I'll search the catalog and put together options.</p>
        <form
          className="chat-hero-input"
          onSubmit={(e) => {
            e.preventDefault();
            send(input);
          }}
        >
          <input
            autoFocus
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="e.g. I need wireless earbuds under 3000 rupees"
          />
          <button className="btn btn-primary" type="submit" disabled={loading}>
            Ask
          </button>
        </form>
        <div className="pill-row" style={{ justifyContent: "center" }}>
          {STARTER_PROMPTS.map((s) => (
            <button key={s} className="pill" type="button" onClick={() => send(s)}>
              {s}
            </button>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="chat-shell">
      <div className="chat-topbar">
        <div>
          <strong>FlowState shopping assistant</strong>
        </div>
        <div style={{ display: "flex", gap: 8, position: "relative" }}>
          <button className="btn" type="button" disabled={resetting} onClick={cancelAndStartOver}>
            {resetting ? "Starting over…" : "Cancel & start over"}
          </button>
          <button className="btn" type="button" onClick={() => setShowTrace((v) => !v)}>
            Agent reasoning
          </button>
          <button className="btn" type="button" onClick={() => setShowCart((v) => !v)}>
            Cart{cartCount > 0 ? ` (${cartCount})` : ""}
          </button>
          {showCart && (
            <div className="dropdown-panel">
              <div className="section-title">Cart</div>
              {cart.length === 0 ? (
                <div className="empty-state">Empty</div>
              ) : (
                <>
                  {cart.map((item) => (
                    <div key={item.sku} className="cart-item">
                      <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <ProductThumb src={catalogImages[item.sku]} alt={item.title} size={28} />
                        {item.title} &times; {item.quantity}
                        {item.discount_percent ? ` (${item.discount_percent}% off)` : ""}
                      </span>
                      <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        {item.original_price_paise ? (
                          <span style={{ textDecoration: "line-through", opacity: 0.55, fontSize: 12 }}>
                            {formatInr(item.original_price_paise * item.quantity)}
                          </span>
                        ) : null}
                        <strong>{formatInr(item.price_paise * item.quantity)}</strong>
                        <button
                          className="cart-remove-btn"
                          type="button"
                          aria-label={`Remove ${item.title}`}
                          disabled={removingSku === item.sku}
                          onClick={() => removeItem(item.sku)}
                        >
                          ×
                        </button>
                      </span>
                    </div>
                  ))}
                  <div className="cart-item" style={{ fontWeight: 700 }}>
                    <span>Total</span>
                    <span>{formatInr(cartTotal)}</span>
                  </div>
                </>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="chat-thread">
        {lines.map((line, i) => (
          <div key={i} className={`chat-turn ${line.role}`}>
            <div className={`chat-bubble ${line.role}`}>{line.text}</div>
            {line.products && line.products.length > 0 && (
              <div className="product-grid">
                {line.products.map((p) => (
                  <ProductCard key={p.sku} product={p} onAdd={(prod) => send(`Add the ${prod.title} to my cart`)} />
                ))}
              </div>
            )}
            {line.paymentMethods && line.paymentMethods.length > 0 && (
              <PaymentMethodPanel
                methods={line.paymentMethods}
                onChoose={(network) => send(`I'll pay with ${network}`)}
              />
            )}
          </div>
        ))}

        {checkoutResult && checkoutResult.status === "approved" && (
          <div className="chat-turn assistant">
            {paymentOutcome[checkoutResult.order_id!] === "paid" && invoice ? (
              <InvoiceView invoice={invoice} />
            ) : (
              <div className="card" style={{ maxWidth: 420 }}>
                <span className="badge badge-good">Gatekeeper approved</span>
                <p style={{ fontSize: 13, marginTop: 10 }}>
                  Order <code>{checkoutResult.order_id}</code> for {formatInr(checkoutResult.amount_paise || 0)}.
                </p>
                {paymentOutcome[checkoutResult.order_id!] === "failed" ? (
                  <p style={{ fontSize: 12.5, color: "var(--status-critical)" }}>
                    Payment declined. Ask me to "try again" to get a fresh payment link for the same cart.
                  </p>
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 6 }}>
                    <button className="btn btn-primary" disabled={paying} onClick={() => simulatePay("paid")}>
                      Simulate: card succeeds
                    </button>
                    <div style={{ display: "flex", gap: 6 }}>
                      <select value={failureCode} onChange={(e) => setFailureCode(e.target.value)} style={{ flex: 1 }}>
                        {FAILURE_SCENARIOS.map((s) => (
                          <option key={s.code} value={s.code}>
                            {s.label}
                          </option>
                        ))}
                      </select>
                      <button className="btn" disabled={paying} onClick={() => simulatePay("failed")}>
                        Simulate decline
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {checkoutResult && checkoutResult.status === "denied" && (
          <div className="chat-turn assistant">
            <div className="card" style={{ maxWidth: 420 }}>
              <span className="badge badge-critical">Gatekeeper denied</span>
              <p style={{ fontSize: 13, marginTop: 10 }}>{checkoutResult.reason}</p>
            </div>
          </div>
        )}

        {loading && (
          <div className="chat-turn assistant">
            <TypingIndicator />
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {showTrace && (
        <div className="trace-drawer">
          <div className="section-title">Agent trace (last turn)</div>
          <TraceView trace={lastTrace} />
        </div>
      )}

      <form
        className="chat-input-bar"
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
      >
        <input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Message the shopping assistant…" disabled={loading} />
        <button className="btn btn-primary" type="submit" disabled={loading}>
          Send
        </button>
      </form>
    </div>
  );
}
