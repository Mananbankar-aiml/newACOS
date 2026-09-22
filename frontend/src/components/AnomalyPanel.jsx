import React, { useState } from "react";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { Activity, Loader2, ChevronDown } from "lucide-react";

const sev = { high: "text-[#e2726f] border-[#e2726f]/30 bg-[#e2726f]/10", medium: "text-yellow-400 border-yellow-500/30 bg-yellow-500/10", low: "text-[#a8a8ad] border-[#2a2a2e] bg-white/5" };

// Statistical + Isolation-Forest scan of invoices (no LLM); the Finance agent explains these results.
export default function AnomalyPanel() {
  const [report, setReport] = useState(null);
  const [busy, setBusy] = useState(false);
  const [open, setOpen] = useState(true);
  const run = async () => {
    setBusy(true);
    try { setReport((await api.get("/finance/anomalies")).data); setOpen(true); }
    catch (e) { toast.error(e?.response?.data?.detail || "Scan failed"); }
    finally { setBusy(false); }
  };
  const flagged = report?.results.filter((r) => r.is_anomaly) || [];
  return (
    <div className="mb-6 rounded-[14px] border border-[#2a2a2e] bg-[#141416] p-5" data-testid="anomaly-panel">
      <div className="flex items-center justify-between gap-4">
        <div>
          <div className="text-[10px] uppercase tracking-[0.25em] text-[#a8a8ad] font-mono-i">ML anomaly detection</div>
          <div className="text-sm text-[#8c8c93] mt-1">Isolation Forest · Benford's law · robust z-scores. Detects; the Finance agent explains; you decide.</div>
        </div>
        <button type="button" data-testid="run-anomaly-scan-btn" onClick={run} disabled={busy}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-[999px] bg-gradient-to-r from-[#a8a8ad] to-[#e2726f] text-black font-bold text-xs uppercase tracking-widest disabled:opacity-50">
          {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Activity className="w-4 h-4" />} Run scan
        </button>
      </div>
      {report && (
        <div className="mt-4" data-testid="anomaly-results">
          <div className="flex flex-wrap gap-2 text-xs font-mono-i">
            <span className="px-3 py-1 rounded-full border border-[#2a2a2e]">model: <b>{report.model}</b></span>
            <span className="px-3 py-1 rounded-full border border-[#2a2a2e]">n = {report.n}</span>
            <span className="px-3 py-1 rounded-full border border-[#e2726f]/30 text-[#e2726f]">flagged: {report.flagged}</span>
            <span className="px-3 py-1 rounded-full border border-[#2a2a2e]">Benford χ² = {report.benford.chi_square} {report.benford.conforms ? "(conforms)" : "(deviates)"}</span>
            <button type="button" onClick={() => setOpen((o) => !o)} className="ml-auto inline-flex items-center gap-1 text-[#8c8c93] hover:text-white">{open ? "Hide" : "Show"} <ChevronDown className={`w-3.5 h-3.5 transition-transform ${open ? "rotate-180" : ""}`} /></button>
          </div>
          {open && (
            <div className="mt-3 space-y-2 max-h-72 overflow-y-auto pr-1">
              {flagged.length === 0 && <div className="text-sm text-[#6f6f76]">No anomalies detected.</div>}
              {flagged.map((r) => (
                <div key={r.id} data-testid={`anomaly-row-${r.number}`} className="flex items-start gap-3 p-3 rounded-[10px] border border-[#2a2a2e] bg-[#0f0f11]">
                  <span className={`px-2 py-0.5 rounded-[999px] text-[10px] uppercase tracking-widest font-mono-i border ${sev[r.severity]}`}>{r.severity}</span>
                  <div className="flex-1 min-w-0 text-sm">
                    <div className="font-semibold">{r.number} · {r.vendor} · ${r.amount.toLocaleString()} <span className="text-[#6f6f76] font-mono-i text-xs">score {r.anomaly_score}</span></div>
                    <ul className="text-xs text-[#8c8c93] mt-1 list-disc pl-4">{r.reasons.map((x) => <li key={x}>{x}</li>)}</ul>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
