import type { ReactElement } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../auth";

export function RequireCustomer({ children }: { children: ReactElement }) {
  const { customer } = useAuth();
  if (!customer) return <Navigate to="/login/customer" replace />;
  return children;
}

export function RequireSeller({ children }: { children: ReactElement }) {
  const { seller } = useAuth();
  if (!seller) return <Navigate to="/login/seller" replace />;
  return children;
}
