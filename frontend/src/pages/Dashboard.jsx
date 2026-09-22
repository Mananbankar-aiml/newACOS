import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Users, Wallet, Boxes, ScrollText, Bot, Sparkles, TrendingUp, AlertTriangle } from "lucide-react";
import { Link } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";

const KPI = ({ icon: Icon, label, value, suffix = "", testid }) => (
  <div data-testid={testid} className="relative overflow-hidden rounded-[14px] border border-[#2a2a2e] bg-[#141416] p-6 hover:border-[#3d3d42] transition-colors">
    <div className="flex items-start justify-between">
      <div className="p-2 rounded-[6px] bg-[#29292d] text-[#a8a8ad]">
        <Icon className="w-5 h-5" />
      </div>
      <div className="text-[10px] uppercase tracking-widest text-[#6f6f76] font-mono-i">Live</div>
    </div>
    <div className="mt-6">
      <div className="text-[10px] uppercase tracking-[0.25em] text-[#6f6f76] font-mono-i">{label}</div>
      <div className="mt-2 font-display font-black text-4xl tracking-tighter text-[#f7f7f8]">
        {value}{suffix}
      </div>
    </div>
  </div>
);

export default function Dashboard() {
  const { user } = useAuth();
  const canSeeApprovals = user?.role !== "employee" && user?.role !== "pending";
  const [kpis, setKpis] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [approvals, setApprovals] = useState([]);

  useEffect(() => {
    api.get("/dashboard/kpis").then((r) => setKpis(r.data)).catch(() => {});
    api.get("/analytics/summary").then((r) => setAnalytics(r.data)).catch(() => {});
    api.get("/approvals")
      .then((r) => setApprovals((r.data || []).filter((x) => x.status === "pending").slice(0, 4)))
      .catch(() => setApprovals([])); // employees are 403 here — show nothing gracefully
  }, []);

  return (
    <div className="space-y-8" data-testid="dashboard-page">
      {/* Hero */}
      <section className="relative overflow-hidden rounded-[14px] border border-[#2a2a2e] bg-[#141416] p-8 md:p-12">
        <div className="relative">
          <div className="text-[10px] uppercase tracking-[0.3em] text-[#6f6f76] font-mono-i mb-3">Command Center</div>
          <h1 className="font-display text-4xl md:text-6xl font-black tracking-tighter text-[#f7f7f8]">
            The agents ran <span className="text-[#a8a8ad]">{kpis?.tasks_today ?? "—"} tasks</span> today.
          </h1>
          <p className="mt-4 text-[#8c8c93] max-w-2xl">Human approvals needed on {kpis?.pending_approvals ?? "—"} decisions. Average agent confidence {kpis?.confidence_avg ?? "—"}%.</p>
          <div className="mt-8 flex flex-wrap gap-3">
            {canSeeApprovals && (
              <Link to="/approvals" data-testid="review-approvals-cta" className="px-5 py-2.5 rounded-[6px] bg-[#f7f7f8] text-[#060607] font-bold text-xs uppercase tracking-widest hover:bg-[#a8a8ad] transition-colors">
                Review approvals
              </Link>
            )}
            <Link to="/agents" className="px-5 py-2.5 rounded-[6px] border border-[#2a2a2e] bg-[#1c1c1f] text-[#8c8c93] font-bold text-xs uppercase tracking-widest hover:bg-[#29292d] hover:text-[#f7f7f8] transition-colors">
              View agents
            </Link>
          </div>
        </div>
      </section>

      {/* KPIs */}
      <section className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KPI testid="kpi-employees" icon={Users} label="Employees" value={kpis?.employees ?? "—"} />
        <KPI testid="kpi-revenue" icon={Wallet} label="Revenue MTD" value={kpis ? `$${(kpis.revenue ?? 0).toLocaleString()}` : "—"} />
        <KPI testid="kpi-stock" icon={Boxes} label="SKUs Tracked" value={kpis?.inventory_items ?? "—"} />
        <KPI testid="kpi-pending" icon={ScrollText} label="Pending Approvals" value={kpis?.pending_approvals ?? "—"} />
      </section>

      {/* Approval queue + anomalies */}
      <section className={`grid grid-cols-1 gap-6 ${canSeeApprovals ? "lg:grid-cols-3" : ""}`}>
        {canSeeApprovals && (
        <div className="lg:col-span-2 rounded-[14px] border border-[#2a2a2e] bg-[#141416] p-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <div className="text-[10px] uppercase tracking-[0.25em] text-[#6f6f76] font-mono-i">Pending human sign-off</div>
              <h3 className="font-display text-2xl font-bold mt-1">Approval Queue</h3>
            </div>
            <Link to="/approvals" className="text-xs uppercase tracking-widest text-[#a8a8ad] hover:text-[#a8a8ad] font-mono-i">Open →</Link>
          </div>
          <div className="space-y-3">
            {approvals.length === 0 && <div className="text-[#6f6f76] text-sm">No approvals pending. Nice.</div>}
            {approvals.map((a) => (
              <div key={a.id} className="flex items-start gap-4 p-4 rounded-[10px] border border-[#2a2a2e] bg-[#0f0f11] hover:border-[#2a2a2e] transition-colors">
                <div className="relative w-2.5 h-2.5 rounded-[999px] mt-2 text-[#e2726f] acos-pulse-ring bg-[#e2726f]/10" />
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-semibold text-white truncate">{a.title}</div>
                  <div className="text-xs text-[#6f6f76] mt-1 line-clamp-2">{a.summary}</div>
                </div>
                <div className="text-right shrink-0">
                  <div className="text-[10px] uppercase tracking-widest text-[#6f6f76] font-mono-i">Conf</div>
                  <div className="font-display font-black text-lg text-white">{a.confidence}%</div>
                </div>
              </div>
            ))}
          </div>
        </div>
        )}

        <div className="rounded-[14px] border border-[#2a2a2e] bg-[#141416] p-6">
          <div className="flex items-center gap-2 mb-6">
            <AlertTriangle className="w-4 h-4 text-[#e2726f]" />
            <div>
              <div className="text-[10px] uppercase tracking-[0.25em] text-[#6f6f76] font-mono-i">Signals</div>
              <h3 className="font-display text-2xl font-bold">Anomalies</h3>
            </div>
          </div>
          <div className="space-y-3">
            {analytics?.anomalies?.map((an) => (
              <div key={an.id} className="p-3 rounded-lg border border-[#2a2a2e] bg-[#0f0f11]">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] uppercase tracking-widest text-[#a8a8ad] font-mono-i">{an.module}</span>
                  <span className={`text-[10px] uppercase tracking-widest font-mono-i ${an.severity === "high" ? "text-[#e2726f]" : an.severity === "medium" ? "text-[#e2726f]" : "text-[#6f6f76]"}`}>{an.severity}</span>
                </div>
                <div className="text-sm text-[#f7f7f8] mt-1.5">{an.message}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Agent overview strip */}
      <section className="rounded-[14px] border border-[#2a2a2e] bg-[#141416] p-6">
        <div className="flex items-center gap-2 mb-6">
          <Bot className="w-4 h-4 text-[#a8a8ad]" />
          <h3 className="font-display text-2xl font-bold">Agent Confidence</h3>
          <div className="ml-auto flex items-center gap-2 text-[#a8a8ad] text-xs font-mono-i uppercase tracking-widest">
            <TrendingUp className="w-3.5 h-3.5" /> +6% w/w
          </div>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          {["Orchestrator","HR","Finance","Inventory","Sales","Compliance"].map((n, i) => {
            const conf = [92, 88, 84, 91, 79, 86][i];
            return (
              <div key={n} className="p-4 rounded-[10px] border border-[#2a2a2e] bg-[#0f0f11]">
                <div className="text-[10px] uppercase tracking-widest text-[#6f6f76] font-mono-i">{n}</div>
                <div className="font-display font-black text-3xl mt-1">{conf}<span className="text-lg text-[#6f6f76]">%</span></div>
                <div className="h-1 mt-3 rounded-[999px] bg-white/5 overflow-hidden">
                  <div className="h-full bg-gradient-to-r from-[#a8a8ad] to-[#e2726f]" style={{ width: `${conf}%` }} />
                </div>
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}
