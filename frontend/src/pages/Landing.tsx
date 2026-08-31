import { Link } from "react-router-dom";
import { useAuth } from "../auth";

export default function Landing() {
  const { customer, seller } = useAuth();

  return (
    <div className="landing">
      <div className="landing-brand">Pulse &amp; Co.</div>
      <p className="landing-sub">Agentic commerce on Razorpay test-mode - built with Strands agents.</p>
      <div className="landing-cards">
        <Link to={customer ? "/chat" : "/login/customer"} className="landing-card">
          <div className="landing-card-kicker">Shop</div>
          <h2>I'm a customer</h2>
          <p>Chat with the shopping assistant, get suggestions, and check out.</p>
          <span className="link-btn">{customer ? `Continue as ${customer.name.split(" ")[0]} →` : "Sign in to shop →"}</span>
        </Link>
        <Link to={seller ? "/dashboard" : "/login/seller"} className="landing-card">
          <div className="landing-card-kicker">Run the store</div>
          <h2>I'm the merchant</h2>
          <p>Revenue, campaigns, and the full gatekeeper audit trail.</p>
          <span className="link-btn">{seller ? `Continue as ${seller.name.split(" ")[0]} →` : "Sign in as seller →"}</span>
        </Link>
      </div>
      <Link to="/ai-buyer" className="link-btn" style={{ marginTop: 28 }}>
        Or try the AI-buyer simulator (no login needed) →
      </Link>
    </div>
  );
}
