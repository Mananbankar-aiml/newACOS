import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import PageHeader from "@/components/PageHeader";

export default function AuditLogs() {
  const [logs, setLogs] = useState([]);
  const [q, setQ] = useState("");
  useEffect(() => { api.get("/audit-logs").then((r) => setLogs(r.data)); }, []);
  const filtered = logs.filter((l) => {
    const s = `${l.actor} ${l.action} ${l.module} ${l.details}`.toLowerCase();
    return s.includes(q.toLowerCase());
  });
  return (
    <div data-testid="audit-page">
      <PageHeader eyebrow="Accountability" title="Audit Logs">
        <input data-testid="audit-search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search…" className="px-4 py-2 rounded-lg bg-[#141416] border border-[#2a2a2e] text-sm focus:border-[#2a2a2e] outline-none" />
      </PageHeader>
      <div className="rounded-[14px] border border-[#2a2a2e] bg-[#141416] overflow-hidden">
        <table className="w-full text-sm">
          <thead className="text-[10px] uppercase tracking-widest text-[#6f6f76] font-mono-i bg-[#0f0f11]">
            <tr><th className="text-left px-4 py-3">Timestamp</th><th className="text-left">Actor</th><th className="text-left">Module</th><th className="text-left">Action</th><th className="text-left px-4">Details</th></tr>
          </thead>
          <tbody>
            {filtered.map((l) => (
              <tr key={l.id} className="border-t border-[#2a2a2e] hover:bg-white/[0.02]">
                <td className="px-4 py-3 font-mono-i text-xs text-[#6f6f76]">{new Date(l.timestamp).toLocaleString()}</td>
                <td className="text-[#a8a8ad] font-mono-i text-xs">{l.actor}</td>
                <td className="text-[#8c8c93] text-xs uppercase tracking-widest font-mono-i">{l.module}</td>
                <td className="text-[#f7f7f8] text-xs">{l.action}</td>
                <td className="px-4 text-[#f7f7f8]">{l.details}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
