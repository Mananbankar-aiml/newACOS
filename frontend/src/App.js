import React from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { GoogleOAuthProvider } from "@react-oauth/google";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import { Toaster } from "sonner";
import Login from "@/pages/Login";
import SignUp from "@/pages/SignUp";
import VerifyEmail from "@/pages/VerifyEmail";
import ForgotPassword from "@/pages/ForgotPassword";
import ResetPassword from "@/pages/ResetPassword";
import Layout from "@/components/Layout";
import Dashboard from "@/pages/Dashboard";
import Agents from "@/pages/Agents";
import HR from "@/pages/HR";
import Finance from "@/pages/Finance";
import Inventory from "@/pages/Inventory";
import Sales from "@/pages/Sales";
import Compliance from "@/pages/Compliance";
import Analytics from "@/pages/Analytics";
import Approvals from "@/pages/Approvals";
import AuditLogs from "@/pages/AuditLogs";
import Settings from "@/pages/Settings";

function Protected({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="min-h-screen flex items-center justify-center text-[#6f6f76]">Loading…</div>;
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

function Providers({ children }) {
  const clientId = process.env.REACT_APP_GOOGLE_CLIENT_ID;
  return clientId ? <GoogleOAuthProvider clientId={clientId}>{children}</GoogleOAuthProvider> : children;
}

export default function App() {
  return (
    <div className="App">
      <Providers>
        <AuthProvider>
          <BrowserRouter>
            <Toaster theme="dark" position="top-right" richColors />
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route path="/signup" element={<SignUp />} />
              <Route path="/verify" element={<VerifyEmail />} />
              <Route path="/forgot" element={<ForgotPassword />} />
              <Route path="/reset" element={<ResetPassword />} />
              <Route path="/" element={<Protected><Layout /></Protected>}>
                <Route index element={<Dashboard />} />
                <Route path="agents" element={<Agents />} />
                <Route path="hr" element={<HR />} />
                <Route path="finance" element={<Finance />} />
                <Route path="inventory" element={<Inventory />} />
                <Route path="sales" element={<Sales />} />
                <Route path="compliance" element={<Compliance />} />
                <Route path="analytics" element={<Analytics />} />
                <Route path="approvals" element={<Approvals />} />
                <Route path="audit-logs" element={<AuditLogs />} />
                <Route path="settings" element={<Settings />} />
              </Route>
            </Routes>
          </BrowserRouter>
        </AuthProvider>
      </Providers>
    </div>
  );
}
