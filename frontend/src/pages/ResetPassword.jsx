import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";

export default function ResetPassword() {
  const [params] = useSearchParams();
  const nav = useNavigate();
  const [token, setToken] = useState("");
  const [pwd, setPwd] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const t = params.get("token");
    if (t) setToken(t);
  }, [params]);

  const submit = async (e) => {
    e.preventDefault();
    if (pwd.length < 6) { toast.error("Password must be at least 6 characters."); return; }
    setBusy(true);
    try {
      await api.post("/auth/reset", { token, new_password: pwd });
      toast.success("Password updated. Sign in with your new password.");
      nav("/login");
    } catch (err) { toast.error(err?.response?.data?.detail || "Failed."); } finally { setBusy(false); }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#060607] text-white px-6">
      <div className="w-full max-w-md">
        <div className="text-[10px] uppercase tracking-[0.3em] text-[#a8a8ad] font-mono-i mb-2">Set new password</div>
        <h1 className="font-display text-3xl font-black tracking-tight">Reset</h1>
        <form onSubmit={submit} className="mt-8 space-y-4">
          <div>
            <label className="text-[10px] uppercase tracking-[0.2em] text-[#6f6f76] font-mono-i">Reset token</label>
            <input
              type="text"
              data-testid="reset-token"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              required
              className="w-full mt-2 px-4 py-3 rounded-lg bg-[#141416] border border-[#2a2a2e] focus:border-[#2a2a2e] outline-none text-sm font-mono-i"
            />
          </div>
          <div>
            <label className="text-[10px] uppercase tracking-[0.2em] text-[#6f6f76] font-mono-i">New password</label>
            <input
              type="password"
              data-testid="reset-password"
              value={pwd}
              onChange={(e) => setPwd(e.target.value)}
              required
              minLength={6}
              className="w-full mt-2 px-4 py-3 rounded-lg bg-[#141416] border border-[#2a2a2e] focus:border-[#2a2a2e] outline-none text-sm"
            />
          </div>
          <button
            disabled={busy}
            data-testid="reset-submit"
            className="w-full py-3 rounded-lg bg-gradient-to-r from-[#a8a8ad] to-[#e2726f] text-black font-black uppercase tracking-widest text-sm disabled:opacity-50"
          >{busy ? "Updating…" : "Update password"}</button>
        </form>
        <div className="mt-8 text-xs text-[#6f6f76]">
          <Link to="/login" className="text-[#a8a8ad] hover:text-[#a8a8ad]">← Back to login</Link>
        </div>
      </div>
    </div>
  );
}
