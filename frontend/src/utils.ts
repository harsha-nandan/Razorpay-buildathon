import type { TraceItem } from "./api";

/** Safety net: the agent is told not to use markdown, but small/local
 * models don't always follow that reliably - strip common markdown syntax
 * so raw `**`/`_`/`#`/`` ` `` never leaks into a plain-text chat bubble. */
export function stripMarkdown(text: string): string {
  return text
    .replace(/```[\s\S]*?```/g, (block) => block.replace(/```/g, ""))
    .replace(/(\*\*\*|___)(.+?)\1/g, "$2")
    .replace(/(\*\*|__)(.+?)\1/g, "$2")
    .replace(/(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])/g, "$1")
    .replace(/(?<![\w_])_(?!\s)(.+?)(?<!\s)_(?![\w_])/g, "$1")
    .replace(/`([^`]+)`/g, "$1")
    .replace(/^#{1,6}\s+/gm, "")
    .replace(/^>\s?/gm, "")
    .replace(/^[-*+]\s+/gm, "")
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, "$1 ($2)");
}

export interface CheckoutResult {
  status: "approved" | "denied" | "error";
  order_id?: string;
  amount_paise?: number;
  payment_link?: string;
  reason?: string;
}

export interface SuggestedProduct {
  sku: string;
  title: string;
  description: string;
  price_paise: number;
  category: string;
  in_stock: boolean;
  discount_percent?: number;
  discounted_price_paise?: number;
  rating?: number;
  review_count?: number;
  image_url?: string;
}

const PRODUCT_LIST_TOOLS = new Set(["search_catalog", "get_upsell_suggestions"]);

/** Pull product cards out of this turn's tool results, in call order, de-duped by SKU. */
export function extractSuggestedProducts(trace: TraceItem[]): SuggestedProduct[] {
  const bySku = new Map<string, SuggestedProduct>();
  for (const item of trace) {
    if (item.type !== "tool_result" || !item.tool || !PRODUCT_LIST_TOOLS.has(item.tool) || !item.output) continue;
    try {
      const parsed = JSON.parse(item.output);
      if (!Array.isArray(parsed)) continue;
      for (const p of parsed) {
        if (p && typeof p === "object" && p.sku) bySku.set(p.sku, p as SuggestedProduct);
      }
    } catch {
      // not JSON - ignore
    }
  }
  return Array.from(bySku.values());
}

export interface EmiPlan {
  tenure_months: number;
  interest_rate_percent: number;
  no_cost: boolean;
}

export interface ComputedOffer {
  label: string;
  kind: "discount" | "cashback";
  percent: number;
  amount_paise: number;
  price_after_paise: number;
}

export interface PaymentMethodDetail {
  network: string;
  accepted: boolean;
  cart_subtotal_paise: number;
  offers: ComputedOffer[];
  emi_available: boolean;
  emi_min_order_inr: number | null;
  emi_plans: EmiPlan[];
  notes: string;
}

/** The latest check_payment_method tool result this turn, if any. A result
 * with more than one entry means the agent asked "which network?" (render
 * as a choice panel); exactly one means a specific card was looked up
 * (render as a detail card with offers/EMI). */
export function extractPaymentMethodResult(trace: TraceItem[]): PaymentMethodDetail[] | null {
  for (let i = trace.length - 1; i >= 0; i--) {
    const item = trace[i];
    if (item.type === "tool_result" && item.tool === "check_payment_method" && item.output) {
      try {
        const parsed = JSON.parse(item.output);
        if (Array.isArray(parsed)) return parsed as PaymentMethodDetail[];
      } catch {
        return null;
      }
    }
  }
  return null;
}

export function findLatestCheckoutResult(trace: TraceItem[]): CheckoutResult | null {
  for (let i = trace.length - 1; i >= 0; i--) {
    const item = trace[i];
    if (item.type === "tool_result" && item.tool === "checkout" && item.output) {
      try {
        return JSON.parse(item.output) as CheckoutResult;
      } catch {
        return null;
      }
    }
  }
  return null;
}
