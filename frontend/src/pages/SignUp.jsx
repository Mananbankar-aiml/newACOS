import React, { useState } from "react";
import { useNavigate, Link, Navigate } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";
import { Bot } from "lucide-react";
import GoogleSignInButton from "@/components/GoogleSignInButton";

export default function SignUp() {
  const { user } = useAuth();
  const nav = useNavigate();
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/" replace />;

  const submit = async (e) => {
    e.preventDefault();
    if (form.password.length < 6) { toast.error("Password must be 6+ chars"); return; }
    setBusy(true);
    try {
      const { data } = await api.post("/auth/register", { ...form, role: "employee" });
      localStorage.setItem("acos_token", data.token);
      toast.success("Account created — check your email for a verification code.");
      window.location.href = "/verify";
    } catch (e) { toast.error(e?.response?.data?.detail || "Sign up failed"); } finally { setBusy(false); }
  };

  return (
    <div className="relative min-h-screen w-full flex bg-[#060607] text-white overflow-hidden">
      <div className="hidden lg:flex relative w-1/2 border-r border-[#2a2a2e] overflow-hidden">
        <div className="absolute inset-0 acos-grid-bg opacity-60" />
        <div className="absolute -top-20 -left-20 w-[600px] h-[600px] acos-aurora rounded-[999px]" />
        <div className="relative z-10 flex flex-col justify-between p-14 w-full">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-[#a8a8ad] to-[#e2726f] shadow-none" />
            <div className="font-display font-black text-2xl tracking-tight">ACOS</div>
          </div>
          <div>
            <div className="text-xs font-mono-i uppercase tracking-[0.3em] text-[#a8a8ad] mb-6">Create account</div>
            <h1 className="font-display text-5xl xl:text-6xl font-black tracking-tighter leading-[0.95]">
              Ship your company<br />
              <span className="bg-gradient-to-r from-[#a8a8ad] to-[#e2726f] bg-clip-text text-transparent">on autopilot.</span>
            </h1>
            <p className="mt-6 text-[#8c8c93] max-w-md">Six specialist agents watching HR, Finance, Inventory, Sales, Compliance — with humans still in the loop.</p>
          </div>
          <div className="text-[10px] uppercase tracking-[0.3em] text-[#6f6f76] font-mono-i">v0.3 • Feb 2026</div>
        </div>
      </div>

      <div className="relative flex-1 flex items-center justify-center p-8">
        <div className="w-full max-w-[420px]">
          <div className="mb-8">
            <div className="text-xs font-mono-i uppercase tracking-[0.3em] text-[#a8a8ad] mb-2">Sign up</div>
            <h2 className="font-display text-3xl font-black tracking-tight">Create your account</h2>
            <p className="text-sm text-[#6f6f76] mt-2">Free · no credit card. Verify your email after signup.</p>
          </div>

          <div data-testid="google-signup-btn"><GoogleSignInButton label="signup_with" /></div>

          <div className="flex items-center gap-3 my-6">
            <div className="flex-1 h-px bg-white/10" />
            <span className="text-[10px] uppercase tracking-widest text-[#6f6f76] font-mono-i">or with email</span>
            <div className="flex-1 h-px bg-white/10" />
          </div>

          <form onSubmit={submit} className="space-y-4">
            <div>
              <label className="text-[10px] uppercase tracking-[0.2em] text-[#6f6f76] font-mono-i">Full name</label>
              <input required data-testid="signup-name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
                className="w-full mt-2 px-4 py-3 rounded-lg bg-[#141416] border border-[#2a2a2e] focus:border-[#2a2a2e] outline-none text-sm" />
            </div>
            <div>
              <label className="text-[10px] uppercase tracking-[0.2em] text-[#6f6f76] font-mono-i">Email</label>
              <input required type="email" data-testid="signup-email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })}
                className="w-full mt-2 px-4 py-3 rounded-lg bg-[#141416] border border-[#2a2a2e] focus:border-[#2a2a2e] outline-none text-sm" />
            </div>
            <div>
              <label className="text-[10px] uppercase tracking-[0.2em] text-[#6f6f76] font-mono-i">Password (6+ chars)</label>
              <input required type="password" minLength={6} data-testid="signup-password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })}
                className="w-full mt-2 px-4 py-3 rounded-lg bg-[#141416] border border-[#2a2a2e] focus:border-[#2a2a2e] outline-none text-sm" />
            </div>
            <div className="text-[10px] text-[#6f6f76] font-mono-i uppercase tracking-widest">
              New accounts start as employee · your admin can promote roles from Settings
            </div>
            <button disabled={busy} data-testid="signup-submit"
              className="w-full py-3.5 rounded-lg bg-gradient-to-r from-[#a8a8ad] to-[#e2726f] text-black font-black uppercase tracking-widest text-sm disabled:opacity-50">
              {busy ? "Creating…" : "Create account"}
            </button>
          </form>

          <div className="text-xs text-[#6f6f76] mt-6">
            Already have an account? <Link to="/login" className="text-[#a8a8ad] hover:text-[#a8a8ad]">Sign in</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
