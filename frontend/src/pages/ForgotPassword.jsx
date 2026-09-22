import React, { useState } from "react";
import { api } from "@/lib/api";
import { Link } from "react-router-dom";
import { toast } from "sonner";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await api.post("/auth/forgot", { email });
      setSent(true);
      toast.success("Check your inbox for a reset link.");
    } catch { toast.error("Something went wrong."); } finally { setBusy(false); }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#060607] text-white px-6">
      <div className="w-full max-w-md">
        <div className="text-[10px] uppercase tracking-[0.3em] text-[#a8a8ad] font-mono-i mb-2">Account recovery</div>
        <h1 className="font-display text-3xl font-black tracking-tight">Forgot password</h1>
        <p className="text-sm text-[#6f6f76] mt-2">Enter your email — we'll send a reset link that expires in 30 minutes.</p>

        {sent ? (
          <div className="mt-8 p-4 rounded-[10px] border border-[#2a2a2e] bg-[#29292d] text-[#a8a8ad] text-sm">
            If an account exists for {email}, a reset link is on its way. In demo mode (no Resend key), check the /api/emails endpoint or the audit log for the token.
          </div>
        ) : (
          <form onSubmit={submit} className="mt-8 space-y-4">
            <input
              type="email"
              data-testid="forgot-email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@company.com"
              required
              className="w-full px-4 py-3 rounded-lg bg-[#141416] border border-[#2a2a2e] focus:border-[#2a2a2e] outline-none text-sm"
            />
            <button
              disabled={busy}
              data-testid="forgot-submit"
              className="w-full py-3 rounded-lg bg-gradient-to-r from-[#a8a8ad] to-[#e2726f] text-black font-black uppercase tracking-widest text-sm disabled:opacity-50"
            >{busy ? "Sending…" : "Send reset link"}</button>
          </form>
        )}
        <div className="mt-8 text-xs text-[#6f6f76]">
          <Link to="/login" className="text-[#a8a8ad] hover:text-[#a8a8ad]">← Back to login</Link>
        </div>
      </div>
    </div>
  );
}
