import { formatInr } from "../api";

/** A brief, purely visual "payment happening" beat for the AI Buyer's
 * autonomous x402 handshake - so a viewer sees the payment step occur
 * instead of an instant jump from "approved" straight to "paid". This is
 * cosmetic only: the real confirm call already fires the moment checkout is
 * approved (see AIBuyer.tsx), nothing here waits on or requires a click. */
export default function AutoPaymentPanel({ amountPaise, authorized }: { amountPaise: number; authorized: boolean }) {
  return (
    <div className="card payment-detail-card auto-payment-panel">
      <div className="payment-detail-header">
        <strong>Simulated card payment</strong>
        {authorized ? (
          <span className="badge badge-good">authorized</span>
        ) : (
          <span className="badge badge-muted">processing…</span>
        )}
      </div>
      <div className="payment-detail-section">
        <div className={"auto-payment-card" + (authorized ? " auto-payment-card-done" : "")}>
          <div className="auto-payment-card-row">
            <span>Visa •••• 4242</span>
            <span className="auto-payment-card-exp">EXP 12/29</span>
          </div>
          <div className="auto-payment-card-amount">{formatInr(amountPaise)}</div>
        </div>
        <div className="auto-payment-status">
          {authorized ? (
            <>✓ Charged via Razorpay test-mode - no human clicked anything, the AI buyer completed the x402 handshake's second call automatically.</>
          ) : (
            <span className="auto-payment-status-row">
              <span className="auto-payment-spinner" aria-hidden />
              Authorizing with the issuing bank (test-mode)…
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
