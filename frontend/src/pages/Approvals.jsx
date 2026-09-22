import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";
import { Check, X } from "lucide-react";
import OtpDialog from "@/components/OtpDialog";

const statusPill = (s) => {
  const map = { pending: "bg-[#e2726f]/10 text-[#e2726f] border-yellow-500/30", approved: "bg-[#29292d] text-[#a8a8ad] border-[#2a2a2e]", rejected: "bg-[#e2726f]/10 text-[#e2726f] border-[#e2726f]/30" };
  return `px-2 py-0.5 rounded-[999px] text-[10px] uppercase tracking-widest font-mono-i border ${map[s]}`;
};

export default function Approvals() {
  const [items, setItems] = useState([]);
  const { user } = useAuth();
  const canDecide = user?.role === "admin" || user?.role === "manager";
  const [otpOpen, setOtpOpen] = useState(false);
  const [pendingAction, setPendingAction] = useState(null); // {id, decision}
  const [stepUpToken, setStepUpToken] = useState(null);

  const load = () => api.get("/approvals").then((r) => setItems(r.data));
  useEffect(() => { load(); }, []);

  const executeDecide = async (id, decision, token) => {
    try {
      const headers = token ? { "X-OTP-Token": token } : {};
      await api.post(`/approvals/${id}/decide`, { decision }, { headers });
      toast.success(`Marked ${decision === "approve" ? "approved" : "rejected"}`);
      load();
    } catch (e) {
      if (e?.response?.status === 428) {
        // Step-up required — open OTP dialog and remember action
        setPendingAction({ id, decision });
        setOtpOpen(true);
      } else {
        toast.error(e?.response?.data?.detail || "Failed");
      }
    }
  };

  const decide = (id, decision) => {
    // If admin already holds a step-up token this session, reuse; else attempt first (server will 428 for admin).
    executeDecide(id, decision, stepUpToken);
  };

  const onOtpVerified = (token) => {
    setStepUpToken(token);
    if (pendingAction) {
      const { id, decision } = pendingAction;
      setPendingAction(null);
      executeDecide(id, decision, token);
    }
  };

  return (
    <div data-testid="approvals-page">
      <PageHeader eyebrow="Human in the Loop" title="Approvals Queue" />
      {user?.role === "admin" && (
        <div className="mb-4 text-xs text-[#6f6f76] font-mono-i uppercase tracking-widest">
          Admin actions require email OTP · step-up token valid 15 min
        </div>
      )}
      <div className="space-y-3">
        {items.map((a) => (
          <div key={a.id} data-testid={`approval-${a.id}`} className="p-5 rounded-[14px] border border-[#2a2a2e] bg-[#141416] flex items-start gap-4">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-[#a8a8ad] to-[#e2726f] flex items-center justify-center text-black font-bold font-mono-i text-xs uppercase">{a.agent?.[0] || "A"}</div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-3">
                <span className="text-[10px] uppercase tracking-widest text-[#a8a8ad] font-mono-i">{a.agent}</span>
                <span className={statusPill(a.status)}>{a.status}</span>
              </div>
              <div className="font-display font-bold text-lg mt-1">{a.title}</div>
              <div className="text-sm text-[#8c8c93] mt-1">{a.summary}</div>
            </div>
            <div className="text-right shrink-0">
              <div className="text-[10px] uppercase tracking-widest text-[#6f6f76] font-mono-i">Confidence</div>
              <div className="font-display font-black text-2xl">{a.confidence}%</div>
              {a.status === "pending" && canDecide && (
                <div className="flex gap-2 mt-3 justify-end">
                  <button data-testid={`reject-${a.id}`} onClick={() => decide(a.id, "reject")} className="p-2 rounded-lg border border-[#e2726f]/30 bg-[#e2726f]/10 hover:bg-[#e2726f]/10 text-[#e2726f]"><X className="w-4 h-4" /></button>
                  <button data-testid={`approve-${a.id}`} onClick={() => decide(a.id, "approve")} className="p-2 rounded-lg border border-[#2a2a2e] bg-[#29292d] hover:bg-[#29292d] text-[#a8a8ad]"><Check className="w-4 h-4" /></button>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
      <OtpDialog open={otpOpen} purpose="approval" onClose={() => setOtpOpen(false)} onVerified={onOtpVerified} />
    </div>
  );
}
