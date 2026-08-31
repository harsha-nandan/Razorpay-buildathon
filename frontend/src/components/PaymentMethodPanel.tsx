import { formatInr } from "../api";
import type { PaymentMethodDetail } from "../utils";

/** Mirrors the small "pick one" question panel pattern: a compact bordered
 * card with a short prompt and clickable options - shown when the agent
 * lists every accepted network. Once a specific network is looked up, the
 * same data renders as a detail card with offers and EMI plans instead. */
export default function PaymentMethodPanel({
  methods,
  onChoose,
}: {
  methods: PaymentMethodDetail[];
  onChoose: (network: string) => void;
}) {
  if (methods.length > 1) {
    const accepted = methods.filter((m) => m.accepted);
    return (
      <div className="ask-panel">
        <div className="ask-panel-header">Which card or payment method will you use?</div>
        <div className="pill-row">
          {accepted.map((m) => (
            <button key={m.network} className="pill" type="button" onClick={() => onChoose(m.network)}>
              {m.network}
            </button>
          ))}
        </div>
      </div>
    );
  }

  const method = methods[0];
  if (!method) return null;

  return (
    <div className="card payment-detail-card">
      <div className="payment-detail-header">
        <strong>{method.network}</strong>
        {method.accepted ? (
          <span className="badge badge-good">accepted</span>
        ) : (
          <span className="badge badge-critical">not accepted</span>
        )}
      </div>

      <div className="payment-detail-section">
        <div className="payment-detail-label">Price for your cart</div>
        <div className="cart-item">
          <span>Cart total</span>
          <strong>{formatInr(method.cart_subtotal_paise)}</strong>
        </div>
        {method.offers.length === 0 ? (
          <div className="cart-item">
            <span>No offer on {method.network} right now</span>
            <strong>{formatInr(method.cart_subtotal_paise)}</strong>
          </div>
        ) : (
          method.offers.map((offer, i) => (
            <div key={i} className="cart-item payment-offer-row">
              <span>
                {offer.label}
                <span className="payment-offer-kind"> · {offer.kind === "discount" ? "instant discount" : "cashback"}</span>
              </span>
              <span style={{ textAlign: "right" }}>
                <strong className="offer-amount">
                  {offer.kind === "discount" ? "−" : "+"}
                  {formatInr(offer.amount_paise)}
                </strong>
                <div className="payment-offer-payable">
                  {offer.kind === "discount"
                    ? `pay ${formatInr(offer.price_after_paise)}`
                    : `pay ${formatInr(offer.price_after_paise)}, cashback later`}
                </div>
              </span>
            </div>
          ))
        )}
      </div>

      {method.emi_available && method.emi_plans.length > 0 && (
        <div className="payment-detail-section">
          <div className="payment-detail-label">
            EMI options {method.emi_min_order_inr ? `(orders above ${formatInr(method.emi_min_order_inr * 100)})` : ""}
          </div>
          <table className="emi-table">
            <thead>
              <tr>
                <th>Tenure</th>
                <th>Interest</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {method.emi_plans.map((plan) => (
                <tr key={plan.tenure_months}>
                  <td>{plan.tenure_months} months</td>
                  <td>{plan.no_cost ? "0%" : `${plan.interest_rate_percent}% p.a.`}</td>
                  <td>{plan.no_cost && <span className="badge badge-good">no-cost EMI</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {method.notes && <p className="payment-detail-notes">{method.notes}</p>}
    </div>
  );
}
