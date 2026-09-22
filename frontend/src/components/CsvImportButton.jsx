import React, { useRef, useState } from "react";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { Upload, Loader2 } from "lucide-react";

export default function CsvImportButton({ collection, onImported, label = "Import CSV" }) {
  const ref = useRef(null);
  const [busy, setBusy] = useState(false);

  const onChange = async (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append("file", f);
      const { data } = await api.post(`/import/${collection}`, fd, { headers: { "Content-Type": "multipart/form-data" } });
      toast.success(`Imported ${data.imported} rows${data.errors?.length ? ` · ${data.errors.length} errors` : ""}`);
      if (data.errors?.length) console.warn("CSV errors:", data.errors);
      onImported?.();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Import failed");
    } finally {
      setBusy(false);
      if (ref.current) ref.current.value = "";
    }
  };

  return (
    <label
      data-testid={`import-${collection}-btn`}
      className="inline-flex items-center gap-2 px-3 py-2 rounded-full border border-[#2a2a2e] bg-white/[0.03] hover:bg-white/10 cursor-pointer text-xs font-semibold text-[#f7f7f8] uppercase tracking-widest transition-colors"
    >
      {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Upload className="w-3.5 h-3.5" />}
      {busy ? "Importing…" : label}
      <input ref={ref} type="file" accept=".csv" className="hidden" onChange={onChange} />
    </label>
  );
}
