import React from "react";
import { GoogleLogin } from "@react-oauth/google";
import { api } from "@/lib/api";
import { toast } from "sonner";

const CLIENT_ID = process.env.REACT_APP_GOOGLE_CLIENT_ID;

// Google Identity Services -> id_token -> verified server-side at /api/auth/google.
export default function GoogleSignInButton({ label = "signin_with" }) {
  if (!CLIENT_ID) return null;
  const onSuccess = async ({ credential }) => {
    try {
      const { data } = await api.post("/auth/google", { credential });
      localStorage.setItem("acos_token", data.token);
      toast.success(`Welcome ${data.user.name}!`);
      window.location.href = "/";
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Google sign-in failed");
    }
  };
  return (
    <div className="flex justify-center mb-4" data-testid="google-login-btn">
      <GoogleLogin onSuccess={onSuccess} onError={() => toast.error("Google sign-in was cancelled")} theme="filled_black" shape="pill" text={label} width="360" />
    </div>
  );
}
