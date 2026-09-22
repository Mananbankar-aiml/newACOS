import React, { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Plus, Loader2, Pencil } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";

/**
 * Reusable "add / edit record" dialog.
 * Props:
 *   endpoint: POST target under /api (e.g., "/hr/employees")
 *   editEndpoint: PUT target when editing (defaults to `${endpoint}/${initialValues.id}`)
 *   title: dialog title
 *   fields: [{ name, label, type?, options?, defaultValue?, required? }]
 *   onSaved: (row) => void
 *   initialValues: existing row (edit mode) or null (create mode)
 *   trigger: optional custom trigger element
 */
export default function AddRecordDialog({ endpoint, editEndpoint, title, fields, onSaved, onCreated, buttonLabel = "Add", testid, initialValues = null, trigger }) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const isEdit = !!initialValues;
  const [form, setForm] = useState(() =>
    Object.fromEntries(fields.map((f) => [f.name, initialValues?.[f.name] ?? f.defaultValue ?? ""]))
  );

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const payload = { ...form };
      fields.forEach((f) => {
        if (f.type === "number" && payload[f.name] !== "") payload[f.name] = Number(payload[f.name]);
      });
      let data;
      if (isEdit) {
        const url = editEndpoint || `${endpoint}/${initialValues.id}`;
        ({ data } = await api.put(url, payload));
      } else {
        ({ data } = await api.post(endpoint, payload));
      }
      toast.success(`${title} ${isEdit ? "updated" : "created"}`);
      (onSaved || onCreated)?.(data);
      setOpen(false);
      if (!isEdit) setForm(Object.fromEntries(fields.map((f) => [f.name, f.defaultValue ?? ""])));
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Failed");
    } finally { setBusy(false); }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {trigger || (
          <button
            data-testid={testid || (isEdit ? "edit-record-btn" : "add-record-btn")}
            className={isEdit
              ? "p-1.5 rounded text-[#6f6f76] hover:text-[#a8a8ad] hover:bg-[#29292d]"
              : "inline-flex items-center gap-2 px-4 py-2 rounded-[999px] bg-gradient-to-r from-[#a8a8ad] to-[#e2726f] text-black font-bold text-xs uppercase tracking-widest hover:opacity-90 transition"}
          >
            {isEdit ? <Pencil className="w-3.5 h-3.5" /> : <><Plus className="w-4 h-4" /> {buttonLabel}</>}
          </button>
        )}
      </DialogTrigger>
      <DialogContent className="bg-[#060607] border-[#2a2a2e] text-white max-w-md">
        <DialogHeader>
          <DialogTitle className="font-display text-2xl font-black tracking-tight">
            {isEdit ? `Edit · ${title}` : title}
          </DialogTitle>
        </DialogHeader>
        <form onSubmit={submit} className="space-y-3 mt-2 max-h-[70vh] overflow-y-auto pr-1">
          {fields.map((f) => (
            <div key={f.name}>
              <label className="text-[10px] uppercase tracking-[0.2em] text-[#6f6f76] font-mono-i">{f.label}</label>
              {f.options ? (
                <select
                  value={form[f.name] ?? ""}
                  onChange={(e) => setForm({ ...form, [f.name]: e.target.value })}
                  data-testid={`field-${f.name}`}
                  className="w-full mt-1.5 px-3 py-2 rounded-lg bg-[#141416] border border-[#2a2a2e] focus:border-[#2a2a2e] outline-none text-sm"
                >
                  {f.options.map((opt) => <option key={opt} value={opt}>{opt}</option>)}
                </select>
              ) : (
                <input
                  type={f.type || "text"}
                  value={form[f.name] ?? ""}
                  onChange={(e) => setForm({ ...form, [f.name]: e.target.value })}
                  placeholder={f.placeholder}
                  required={f.required !== false}
                  data-testid={`field-${f.name}`}
                  className="w-full mt-1.5 px-3 py-2 rounded-lg bg-[#141416] border border-[#2a2a2e] focus:border-[#2a2a2e] outline-none text-sm"
                />
              )}
            </div>
          ))}
          <button
            type="submit"
            disabled={busy}
            data-testid="add-record-submit"
            className="w-full mt-4 py-2.5 rounded-lg bg-gradient-to-r from-[#a8a8ad] to-[#e2726f] text-black font-black uppercase tracking-widest text-sm flex items-center justify-center gap-2 disabled:opacity-50"
          >
            {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
            {isEdit ? "Save changes" : "Create"}
          </button>
        </form>
      </DialogContent>
    </Dialog>
  );
}
