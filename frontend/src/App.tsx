import { Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import { RequireCustomer, RequireSeller } from "./components/RequireAuth";
import Landing from "./pages/Landing";
import CustomerLogin from "./pages/CustomerLogin";
import SellerLogin from "./pages/SellerLogin";
import Dashboard from "./pages/Dashboard";
import Chat from "./pages/Chat";
import AIBuyer from "./pages/AIBuyer";
import Campaigns from "./pages/Campaigns";
import Audit from "./pages/Audit";
import Orders from "./pages/Orders";
import MyOrders from "./pages/MyOrders";
import Architecture from "./pages/Architecture";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login/customer" element={<CustomerLogin />} />
      <Route path="/login/seller" element={<SellerLogin />} />
      <Route element={<Layout />}>
        <Route
          path="dashboard"
          element={
            <RequireSeller>
              <Dashboard />
            </RequireSeller>
          }
        />
        <Route
          path="chat"
          element={
            <RequireCustomer>
              <Chat />
            </RequireCustomer>
          }
        />
        <Route path="ai-buyer" element={<AIBuyer />} />
        <Route path="architecture" element={<Architecture />} />
        <Route
          path="my-orders"
          element={
            <RequireCustomer>
              <MyOrders />
            </RequireCustomer>
          }
        />
        <Route
          path="orders"
          element={
            <RequireSeller>
              <Orders />
            </RequireSeller>
          }
        />
        <Route
          path="campaigns"
          element={
            <RequireSeller>
              <Campaigns />
            </RequireSeller>
          }
        />
        <Route
          path="audit"
          element={
            <RequireSeller>
              <Audit />
            </RequireSeller>
          }
        />
      </Route>
    </Routes>
  );
}
