import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";

export default function CustomerLogin() {
  const { loginCustomer, registerCustomer } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      if (mode === "login") {
        await loginCustomer(email, password);
      } else {
        await registerCustomer(name, email, password);
      }
      navigate("/chat");
    } catch (err) {
      setError(String(err instanceof Error ? err.message : err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="landing-brand" style={{ marginBottom: 4 }}>
          Pulse &amp; Co.
        </div>
        <h1>{mode === "login" ? "Customer sign in" : "Create a customer account"}</h1>
        <form onSubmit={submit}>
          {mode === "register" && (
            <div className="form-row">
              <label>Name</label>
              <input required value={name} onChange={(e) => setName(e.target.value)} />
            </div>
          )}
          <div className="form-row">
            <label>Email</label>
            <input required type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div className="form-row">
            <label>Password</label>
            <input required type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          </div>
          {error && <p style={{ color: "var(--status-critical)", fontSize: 12.5 }}>{error}</p>}
          <button className="btn btn-primary" type="submit" disabled={loading} style={{ width: "100%" }}>
            {loading ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}
          </button>
        </form>
        <p className="auth-switch">
          {mode === "login" ? (
            <>
              New here?{" "}
              <button className="link-btn" onClick={() => setMode("register")}>
                Create an account
              </button>
            </>
          ) : (
            <>
              Already have an account?{" "}
              <button className="link-btn" onClick={() => setMode("login")}>
                Sign in
              </button>
            </>
          )}
        </p>
        <p className="auth-demo-hint">
          Demo login: <code>ananya.rao@example.com</code> / <code>customer123</code>
        </p>
        <Link className="link-btn" to="/login/seller">
          I'm the merchant, take me to seller sign in →
        </Link>
      </div>
    </div>
  );
}
