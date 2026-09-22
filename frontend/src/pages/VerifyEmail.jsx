import React, { useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { Loader2, ShieldCheck } from "lucide-react";
import { Navigate } from "react-router-dom";

export default function VerifyEmail() {
  const { user, loading } = useAuth();
  const [otp, setOtp] = useState("");
  const [busy, setBusy] = useState(false);
  const [demoHint, setDemoHint] = useState(null);

  if (loading) return <div className="min-h-screen flex items-center justify-center text-[#6f6f76]">Loading…</div>;
  if (!user) return <Navigate to="/login" replace />;
  if (user.email_verified) return <Navigate to="/" replace />;

  const verify = async () => {
    if (otp.length !== 6) { toast.error("Enter the 6-digit code"); return; }
    setBusy(true);
    try {
      await api.post("/auth/verify-email", { otp });
      toast.success("Email verified!");
      window.location.href = "/";
    } catch (e) { toast.error(e?.response?.data?.detail || "Invalid code"); } finally { setBusy(false); }
  };

  const resend = async () => {
    setBusy(true);
    try {
      const { data } = await api.post("/auth/verify-email/resend");
      if (data.demo_hint) { setDemoHint(data.demo_hint); toast.info(`Demo mode · code: ${data.demo_hint}`); }
      else toast.success("New code sent to your inbox.");
    } catch { toast.error("Resend failed"); } finally { setBusy(false); }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#060607] text-white px-6">
      <div className="w-full max-w-sm">
        <div className="w-12 h-12 rounded-[10px] bg-[#29292d] text-[#a8a8ad] flex items-center justify-center mb-4"><ShieldCheck className="w-6 h-6" /></div>
        <div className="text-[10px] uppercase tracking-[0.3em] text-[#a8a8ad] font-mono-i">Verify email</div>
        <h1 className="font-display text-3xl font-black tracking-tight mt-1">Check your inbox</h1>
        <p className="text-sm text-[#6f6f76] mt-2">We sent a 6-digit code to <span className="text-[#a8a8ad] font-mono-i">{user.email}</span>.</p>

        <input
          data-testid="verify-otp-input"
          value={otp}
          onChange={(e) => setOtp(e.target.value.replace(/\D/g, "").slice(0, 6))}
          placeholder="123456"
          className="w-full mt-6 px-4 py-3 rounded-lg bg-[#141416] border border-[#2a2a2e] focus:border-[#2a2a2e] outline-none text-center text-2xl tracking-[0.5em] font-mono-i"
        />
        {demoHint && <div className="mt-2 text-[11px] text-[#e2726f] font-mono-i">Demo hint: {demoHint} (add RESEND_API_KEY for real emails)</div>}

        <button onClick={verify} disabled={busy} data-testid="verify-submit"
          className="mt-4 w-full py-3 rounded-lg bg-gradient-to-r from-[#a8a8ad] to-[#e2726f] text-black font-black uppercase tracking-widest text-sm disabled:opacity-50 flex items-center justify-center gap-2">
          {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : null} Verify
        </button>
        <button onClick={resend} disabled={busy} data-testid="verify-resend"
          className="mt-3 w-full py-2.5 rounded-lg border border-[#2a2a2e] bg-white/[0.02] hover:bg-white/10 text-xs font-semibold uppercase tracking-widest text-[#f7f7f8]">
          Resend code
        </button>
        <div className="mt-6 text-xs text-[#6f6f76]">Wrong email? <a href="/login" className="text-[#a8a8ad] hover:text-[#a8a8ad]">Sign in as someone else</a></div>
      </div>
    </div>
  );
}
