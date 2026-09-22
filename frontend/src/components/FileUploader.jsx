import React, { useRef, useState } from "react";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { Upload, Loader2, Paperclip } from "lucide-react";

/**
 * Compact file uploader chip. Optionally attaches the uploaded file to
 * an invoice or contract via the `attachTo` prop, formatted as
 * "invoice:<id>" or "contract:<id>".
 */
export default function FileUploader({ attachTo, onUploaded, label = "Attach" }) {
  const inputRef = useRef(null);
  const [busy, setBusy] = useState(false);

  const onChange = async (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append("file", f);
      const url = attachTo ? `/files/upload?attach_to=${encodeURIComponent(attachTo)}` : "/files/upload";
      const { data } = await api.post(url, fd, { headers: { "Content-Type": "multipart/form-data" } });
      toast.success(`Uploaded ${f.name}`);
      onUploaded?.(data);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Upload failed");
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  return (
    <label className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-[#2a2a2e] bg-white/[0.03] hover:bg-white/10 cursor-pointer text-xs font-semibold text-[#f7f7f8] transition-colors">
      {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Paperclip className="w-3.5 h-3.5" />}
      <span>{busy ? "Uploading…" : label}</span>
      <input ref={inputRef} type="file" className="hidden" onChange={onChange} accept=".pdf,.png,.jpg,.jpeg,.webp,.csv,.txt" data-testid="file-input" />
    </label>
  );
}
