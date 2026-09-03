import { formatInr, type Invoice } from "../api";

export default function InvoiceView({ invoice, onClose }: { invoice: Invoice; onClose?: () => void }) {
  return (
    <div className="invoice">
      <div className="invoice-header">
        <div>
          <div className="invoice-brand">FlowState</div>
          <div className="invoice-meta">Electronics Accessories &middot; Razorpay test-mode</div>
        </div>
        <div className="invoice-number">
          <div className="invoice-meta">Invoice</div>
          <strong>{invoice.invoice_number}</strong>
          <div className="invoice-meta">{new Date(invoice.issued_at).toLocaleString()}</div>
        </div>
      </div>

      <div className="invoice-billto">
        <div className="invoice-meta">Billed to</div>
        <strong>{invoice.customer_name}</strong>
        <div className="invoice-meta">{invoice.customer_email}</div>
      </div>

      <table className="invoice-table">
        <thead>
          <tr>
            <th>Item</th>
            <th>Qty</th>
            <th>Unit price</th>
            <th>Amount</th>
          </tr>
        </thead>
        <tbody>
          {invoice.items.map((item, i) => (
            <tr key={i}>
              <td className="primary">{item.title}</td>
              <td>{item.quantity}</td>
              <td>{formatInr(item.price_paise)}</td>
              <td>{formatInr(item.price_paise * item.quantity)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="invoice-totals">
        <div className="invoice-totals-row">
          <span>Subtotal</span>
          <span>{formatInr(invoice.subtotal_paise)}</span>
        </div>
        <div className="invoice-totals-row">
          <span>GST (18%)</span>
          <span>{formatInr(invoice.tax_paise)}</span>
        </div>
        <div className="invoice-totals-row invoice-total-final">
          <span>Total paid</span>
          <span>{formatInr(invoice.total_paise)}</span>
        </div>
      </div>

      <div className="invoice-actions no-print">
        <button className="btn btn-primary" type="button" onClick={() => window.print()}>
          Print / Save PDF
        </button>
        {onClose && (
          <button className="btn" type="button" onClick={onClose}>
            Close
          </button>
        )}
      </div>
    </div>
  );
}
