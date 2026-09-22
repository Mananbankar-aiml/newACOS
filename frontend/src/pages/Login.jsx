import React, { useState } from "react";
import { useNavigate, Navigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";
import { Bot, ShieldCheck, Zap } from "lucide-react";
import GoogleSignInButton from "@/components/GoogleSignInButton";

export default function Login() {
  const { user, login } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/" replace />;

  const submit = async (e) => {
    e?.preventDefault?.();
    setBusy(true);
    try {
      await login(email, password);
      toast.success("Signed in.");
      nav("/");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Login failed");
    } finally { setBusy(false); }
  };

  return (
    <div className="relative min-h-screen w-full flex bg-[#060607] text-white overflow-hidden">
      {/* Left: brand */}
      <div className="hidden lg:flex relative w-1/2 border-r border-[#2a2a2e] overflow-hidden">
        <div className="absolute inset-0 acos-grid-bg opacity-60" />
        <div className="absolute -top-20 -left-20 w-[600px] h-[600px] acos-aurora rounded-[999px]" />
        <div className="relative z-10 flex flex-col justify-between p-14 w-full">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-[#a8a8ad] to-[#e2726f] shadow-none" />
            <div className="font-display font-black text-2xl tracking-tight">ACOS</div>
          </div>

          <div>
            <div className="text-xs font-mono-i uppercase tracking-[0.3em] text-[#a8a8ad] mb-6">Autonomous Company OS</div>
            <h1 className="font-display text-5xl xl:text-6xl font-black tracking-tighter leading-[0.95]">
              Six specialist agents.<br />
              <span className="bg-gradient-to-r from-[#a8a8ad] to-[#e2726f] bg-clip-text text-transparent">One command center.</span>
            </h1>
            <p className="mt-6 text-[#8c8c93] text-base max-w-md">
              HR, Finance, Inventory, Sales, Compliance — all supervised by an Orchestrator, all
              gated by a human-in-the-loop approval layer.
            </p>
            <div className="grid grid-cols-3 gap-3 mt-10 max-w-md">
              {[
                { Icon: Bot, label: "6 AI agents" },
                { Icon: ShieldCheck, label: "Human gates" },
                { Icon: Zap, label: "Real-time" },
              ].map(({ Icon, label }) => (
                <div key={label} className="border border-[#2a2a2e] rounded-[10px] p-4 bg-white/[0.02]">
                  <Icon className="w-5 h-5 text-[#a8a8ad] mb-2" />
                  <div className="text-xs font-semibold uppercase tracking-widest text-[#f7f7f8] font-mono-i">{label}</div>
                </div>
              ))}
            </div>
          </div>
          <div className="text-[10px] uppercase tracking-[0.3em] text-[#6f6f76] font-mono-i">v0.1 • Feb 2026</div>
        </div>
      </div>

      {/* Right: form */}
      <div className="relative flex-1 flex items-center justify-center p-8">
        <div className="w-full max-w-[420px]">
          <div className="mb-8">
            <div className="text-xs font-mono-i uppercase tracking-[0.3em] text-[#a8a8ad] mb-2">Sign in</div>
            <h2 className="font-display text-3xl font-black tracking-tight">Access the Command Center</h2>
            <p className="text-sm text-[#6f6f76] mt-2">Continue with Google or your registered email.</p>
          </div>

          <GoogleSignInButton />

          <div className="flex items-center gap-3 mb-4">
            <div className="flex-1 h-px bg-white/10" />
            <span className="text-[10px] uppercase tracking-widest text-[#6f6f76] font-mono-i">or</span>
            <div className="flex-1 h-px bg-white/10" />
          </div>

          <form onSubmit={submit} className="space-y-4">
            <div>
              <label className="text-[10px] uppercase tracking-[0.2em] text-[#6f6f76] font-mono-i">Email</label>
              <input
                type="email"
                data-testid="login-email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full mt-2 px-4 py-3 rounded-lg bg-[#141416] border border-[#2a2a2e] focus:border-[#2a2a2e] outline-none text-sm"
              />
            </div>
            <div>
              <label className="text-[10px] uppercase tracking-[0.2em] text-[#6f6f76] font-mono-i">Password</label>
              <input
                type="password"
                data-testid="login-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full mt-2 px-4 py-3 rounded-lg bg-[#141416] border border-[#2a2a2e] focus:border-[#2a2a2e] outline-none text-sm"
              />
            </div>
            <button
              type="submit"
              disabled={busy}
              data-testid="login-submit"
              className="w-full py-3.5 rounded-lg bg-gradient-to-r from-[#a8a8ad] to-[#e2726f] text-black font-black uppercase tracking-widest text-sm hover:opacity-90 transition-opacity disabled:opacity-50"
            >
              {busy ? "Signing in…" : "Enter"}
            </button>
          </form>

          <div className="text-[10px] text-[#6f6f76] uppercase tracking-widest mt-6 font-mono-i">
            JWT auth · bcrypt hashed · roles enforced server-side
          </div>
          <div className="text-xs text-[#6f6f76] mt-4 flex items-center justify-between">
            <a href="/forgot" data-testid="forgot-link" className="text-[#a8a8ad] hover:text-[#a8a8ad]">Forgot your password?</a>
            <a href="/signup" data-testid="signup-link" className="text-[#a8a8ad] hover:text-[#a8a8ad]">Create account</a>
          </div>
        </div>
      </div>
    </div>
  );
}
