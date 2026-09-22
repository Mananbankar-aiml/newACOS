import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import FileUploader from "@/components/FileUploader";
import AddRecordDialog from "@/components/AddRecordDialog";
import CsvImportButton from "@/components/CsvImportButton";
import CsvExportButton from "@/components/CsvExportButton";
import { useAuth } from "@/context/AuthContext";
import { Paperclip, Trash2 } from "lucide-react";
import { toast } from "sonner";

const contractFields = [
  { name: "title", label: "Contract title", required: true, defaultValue: "" },
  { name: "party", label: "Counterparty", required: true, defaultValue: "" },
  { name: "expires", label: "Expiry date", type: "date", required: true, defaultValue: "" },
  { name: "risk", label: "Risk level", options: ["low", "medium", "high"], defaultValue: "low" },
];

const riskPill = (r) => {
  const map = { low: "bg-[#29292d] text-[#a8a8ad] border-[#2a2a2e]", medium: "bg-[#e2726f]/10 text-[#e2726f] border-yellow-500/30", high: "bg-[#e2726f]/10 text-[#e2726f] border-[#e2726f]/30" };
  return `px-2 py-0.5 rounded-[999px] text-[10px] uppercase tracking-widest font-mono-i border ${map[r]}`;
};

export default function Compliance() {
  const [contracts, setContracts] = useState([]);
  const [error, setError] = useState(null);
  const { user } = useAuth();
  const canWrite = user?.role === "admin" || user?.role === "manager";
  const load = () => api.get("/compliance/contracts").then((r) => { setContracts(r.data); setError(null); }).catch((e) => setError(e?.response?.status === 403 ? "Your role can't view Compliance." : "Failed to load."));
  useEffect(() => { load(); }, []);
  const del = async (id) => { try { await api.delete(`/compliance/contracts/${id}`); toast.success("Deleted"); load(); } catch (e) { toast.error(e?.response?.data?.detail || "Failed"); } };
  if (error) return <div data-testid="compliance-page"><PageHeader eyebrow="Legal & Risk" title="Compliance" /><div className="p-6 rounded-[14px] border border-[#e2726f]/30 bg-[#e2726f]/10 text-[#e2726f] text-sm">{error}</div></div>;
  return (
    <div data-testid="compliance-page">
      <PageHeader eyebrow="Legal & Risk" title="Compliance">
        {canWrite && (
          <div className="flex gap-2">
            <CsvImportButton collection="contracts" onImported={load} label="Import CSV" />
            <CsvExportButton collection="contracts" />
            <AddRecordDialog
              testid="add-contract-btn"
              endpoint="/compliance/contracts"
              title="Add Contract"
              buttonLabel="Add contract"
              fields={contractFields}
              onSaved={load}
            />
          </div>
        )}
      </PageHeader>
      <div className="rounded-[14px] border border-[#2a2a2e] bg-[#141416] p-6 overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-[10px] uppercase tracking-widest text-[#6f6f76] font-mono-i">
            <tr className="border-b border-[#2a2a2e]"><th className="text-left py-2">Title</th><th className="text-left">Party</th><th className="text-left">Expires</th><th className="text-left">Risk</th><th className="text-right">Docs</th></tr>
          </thead>
          <tbody>
            {contracts.map((c) => (
              <tr key={c.id} className="border-b border-[#2a2a2e] hover:bg-white/[0.02]">
                <td className="py-3 font-medium">{c.title}</td>
                <td className="text-[#8c8c93]">{c.party}</td>
                <td className="font-mono-i text-[#f7f7f8]">{c.expires}</td>
                <td><span className={riskPill(c.risk)}>{c.risk}</span></td>
                <td className="text-right">
                  <div className="flex items-center gap-2 justify-end">
                    {(c.attachments?.length || 0) > 0 && (<span className="inline-flex items-center gap-1 text-xs text-[#a8a8ad]"><Paperclip className="w-3 h-3" /> {c.attachments.length}</span>)}
                    <FileUploader attachTo={`contract:${c.id}`} onUploaded={load} />
                    {canWrite && <button onClick={() => del(c.id)} data-testid={`del-contract-${c.id}`} className="p-1.5 rounded text-[#6f6f76] hover:text-[#e2726f] hover:bg-[#e2726f]/10"><Trash2 className="w-3.5 h-3.5" /></button>}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
