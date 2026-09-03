import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";

export default function Layout() {
  const { customer, seller, logoutCustomer, logoutSeller } = useAuth();
  const navigate = useNavigate();

  const links = [
    { to: "/architecture", label: "Architecture" },
    seller ? { to: "/dashboard", label: "Dashboard" } : null,
    customer ? { to: "/chat", label: "Checkout Chat" } : null,
    customer ? { to: "/my-orders", label: "My Orders" } : null,
    { to: "/ai-buyer", label: "AI Buyer" },
    seller ? { to: "/orders", label: "Orders" } : null,
    seller ? { to: "/campaigns", label: "Campaigns" } : null,
    seller ? { to: "/audit", label: "Audit Trail" } : null,
  ].filter((l): l is { to: string; label: string } => l !== null);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand" onClick={() => navigate("/")} style={{ cursor: "pointer" }}>
          FlowState
          <small>Agentic commerce on Razorpay</small>
        </div>
        {links.map((link) => (
          <NavLink key={link.to} to={link.to} className={({ isActive }) => "nav-link" + (isActive ? " active" : "")}>
            {link.label}
          </NavLink>
        ))}

        <div style={{ marginTop: "auto", paddingTop: 16, display: "flex", flexDirection: "column", gap: 8 }}>
          {customer && (
            <div className="sidebar-account">
              <div className="sidebar-account-role">Customer</div>
              <div className="sidebar-account-name">{customer.name}</div>
              <button
                className="link-btn"
                onClick={() => {
                  logoutCustomer();
                  navigate("/");
                }}
              >
                Sign out
              </button>
            </div>
          )}
          {seller && (
            <div className="sidebar-account">
              <div className="sidebar-account-role">Seller</div>
              <div className="sidebar-account-name">{seller.name}</div>
              <button
                className="link-btn"
                onClick={() => {
                  logoutSeller();
                  navigate("/");
                }}
              >
                Sign out
              </button>
            </div>
          )}
          {!customer && (
            <NavLink to="/login/customer" className="nav-link">
              Customer sign in
            </NavLink>
          )}
          {!seller && (
            <NavLink to="/login/seller" className="nav-link">
              Seller sign in
            </NavLink>
          )}
        </div>
      </aside>
      <div className="main-content">
        <Outlet />
      </div>
    </div>
  );
}
