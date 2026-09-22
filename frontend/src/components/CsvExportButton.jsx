import React, { useState } from "react";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { Download, Loader2 } from "lucide-react";

export default function CsvExportButton({ collection, label = "Export CSV" }) {
  const [busy, setBusy] = useState(false);

  const onClick = async () => {
    setBusy(true);
    try {
      const res = await api.get(`/export/${collection}`, { responseType: "blob" });
      const blob = new Blob([res.data], { type: "text/csv" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      const today = new Date().toISOString().slice(0, 10).replace(/-/g, "");
      a.download = `${collection}-${today}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      toast.success(`Exported ${collection}`);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Export failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <button
      onClick={onClick}
      disabled={busy}
      data-testid={`export-${collection}-btn`}
      className="inline-flex items-center gap-2 px-3 py-2 rounded-full border border-[#2a2a2e] bg-white/[0.03] hover:bg-white/10 cursor-pointer text-xs font-semibold text-[#f7f7f8] uppercase tracking-widest transition-colors disabled:opacity-50"
    >
      {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />}
      {busy ? "Exporting…" : label}
    </button>
  );
}
