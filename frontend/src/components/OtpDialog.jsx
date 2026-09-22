import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { X, ShieldCheck, Loader2 } from "lucide-react";

/**
 * Modal that requests + verifies an email OTP and returns a step-up token via `onVerified(token)`.
 * Used before admin/finance-sensitive actions (approvals decide).
 */
export default function OtpDialog({ open, purpose, onClose, onVerified }) {
  const [otp, setOtp] = useState("");
  const [demoHint, setDemoHint] = useState(null);
  const [busy, setBusy] = useState(false);
  const [requested, setRequested] = useState(false);

  useEffect(() => {
    if (!open) { setOtp(""); setDemoHint(null); setRequested(false); return; }
    (async () => {
      setBusy(true);
      try {
        const { data } = await api.post("/auth/otp/request", { purpose });
        setDemoHint(data.demo_hint); // present when Resend key is not set
        setRequested(true);
        if (data.demo_hint) toast.info(`Demo mode — code: ${data.demo_hint}`);
        else toast.success("Verification code sent to your email.");
      } catch (e) { toast.error("Failed to send code"); onClose?.(); } finally { setBusy(false); }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, purpose]);

  if (!open) return null;

  const verify = async () => {
    if (otp.length !== 6) { toast.error("Enter the 6-digit code"); return; }
    setBusy(true);
    try {
      const { data } = await api.post("/auth/otp/verify", { otp, purpose });
      toast.success("Verified — action authorized for 15 min.");
      onVerified(data.step_up_token);
      onClose?.();
    } catch (e) { toast.error(e?.response?.data?.detail || "Invalid code"); } finally { setBusy(false); }
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-[#0f0f11] p-4" data-testid="otp-dialog">
      <div className="w-full max-w-sm rounded-[14px] border border-[#2a2a2e] bg-[#060607] p-6 relative">
        <button onClick={onClose} className="absolute top-3 right-3 p-1 text-[#6f6f76] hover:text-white" data-testid="otp-close"><X className="w-4 h-4" /></button>
        <div className="w-12 h-12 rounded-[10px] bg-[#29292d] text-[#a8a8ad] flex items-center justify-center mb-4"><ShieldCheck className="w-6 h-6" /></div>
        <div className="text-[10px] uppercase tracking-[0.25em] text-[#a8a8ad] font-mono-i">Step-up auth</div>
        <h2 className="font-display text-xl font-bold mt-1">Verify with email OTP</h2>
        <p className="text-sm text-[#8c8c93] mt-1">Admin actions require a fresh 6-digit code sent to your registered email.</p>

        <div className="mt-5">
          <input
            data-testid="otp-input"
            value={otp}
            onChange={(e) => setOtp(e.target.value.replace(/\D/g, "").slice(0, 6))}
            placeholder="123456"
            className="w-full px-4 py-3 rounded-lg bg-[#141416] border border-[#2a2a2e] focus:border-[#2a2a2e] outline-none text-center text-2xl tracking-[0.5em] font-mono-i"
          />
          {demoHint && (
            <div className="mt-2 text-[11px] text-[#e2726f] font-mono-i">Demo hint: {demoHint} (Resend key not configured — real emails require RESEND_API_KEY)</div>
          )}
        </div>

        <button
          onClick={verify}
          disabled={busy || !requested}
          data-testid="otp-verify-btn"
          className="mt-5 w-full py-3 rounded-lg bg-gradient-to-r from-[#a8a8ad] to-[#e2726f] text-black font-black uppercase tracking-widest text-sm disabled:opacity-50 flex items-center justify-center gap-2"
        >
          {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
          Verify
        </button>
      </div>
    </div>
  );
}
