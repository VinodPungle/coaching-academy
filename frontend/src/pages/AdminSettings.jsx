// Admin-only platform-wide payment settings ("/app/settings") — toggling
// portal_mode between live/demo (demo mode lets any paid course be
// enrolled free platform-wide, used for public demos), plus the UPI QR
// code + VPA students see when paying offline.
import { useEffect, useState } from "react";
import { api, uploadFile, fileUrl, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Upload, Trash2, ToggleLeft, ToggleRight, Save } from "lucide-react";

export default function AdminSettings() {
  const [s, setS] = useState(null);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);

  const load = () => api.get("/settings/public").then((r) => setS(r.data));
  useEffect(() => { load(); }, []);

  if (!s) return <p className="text-sm text-zinc-500" data-testid="settings-loading">Loading…</p>;

  const save = async (patch) => {
    setSaving(true);
    try {
      const { data } = await api.put("/admin/settings", patch);
      setS(data);
      toast.success("Settings saved");
    } catch (err) { toast.error(formatApiError(err)); }
    finally { setSaving(false); }
  };

  const handleQrUpload = async (file) => {
    if (!file) return;
    setUploading(true);
    try {
      const res = await uploadFile(file);
      await save({ upi_qr_url: res.url });
    } catch (err) { toast.error(formatApiError(err)); }
    finally { setUploading(false); }
  };

  const clearQr = () => save({ upi_qr_url: "" });

  const toggleMode = () => save({ portal_mode: s.portal_mode === "demo" ? "live" : "demo" });

  return (
    <div className="max-w-3xl space-y-8" data-testid="admin-settings-page">
      <div>
        <p className="text-xs uppercase tracking-[0.2em] font-semibold text-red-600">Admin Panel</p>
        <h1 className="font-heading text-3xl font-black tracking-tight mt-1">Portal Settings</h1>
      </div>

      <section className="border border-zinc-200 p-6 space-y-4">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="font-heading text-xl font-bold">Portal Mode</h2>
            <p className="text-sm text-zinc-500 mt-2 max-w-lg">
              In <b>Demo mode</b>, students can enrol in any course for free — useful for previews and marketing.
              In <b>Live mode</b>, paid courses require the admin to record a UPI/offline payment before granting access.
            </p>
          </div>
          <button
            onClick={toggleMode}
            disabled={saving}
            data-testid="portal-mode-toggle"
            className={`shrink-0 inline-flex items-center gap-2 px-5 py-2.5 font-semibold ${s.portal_mode === "demo" ? "bg-amber-500 text-zinc-950" : "bg-zinc-950 text-white"}`}
          >
            {s.portal_mode === "demo" ? <><ToggleRight className="w-5 h-5" /> Demo mode</> : <><ToggleLeft className="w-5 h-5" /> Live mode</>}
          </button>
        </div>
      </section>

      <section className="border border-zinc-200 p-6 space-y-5">
        <div>
          <h2 className="font-heading text-xl font-bold">UPI Payment Details</h2>
          <p className="text-sm text-zinc-500 mt-2">Displayed to students on paid course checkout screens.</p>
        </div>

        <div>
          <label className="text-xs uppercase tracking-[0.15em] font-semibold text-zinc-500">UPI VPA (Virtual Payment Address)</label>
          <div className="flex gap-2 mt-1">
            <input
              data-testid="upi-vpa-input"
              value={s.upi_vpa || ""}
              onChange={(e) => setS({ ...s, upi_vpa: e.target.value })}
              placeholder="rohini@upi"
              className="flex-1 border border-zinc-300 px-3 py-2 text-sm"
            />
            <button data-testid="upi-vpa-save" onClick={() => save({ upi_vpa: s.upi_vpa || "" })} disabled={saving} className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-semibold bg-blue-700 text-white hover:bg-blue-900 disabled:opacity-50">
              <Save className="w-3.5 h-3.5" /> Save
            </button>
          </div>
        </div>

        <div>
          <label className="text-xs uppercase tracking-[0.15em] font-semibold text-zinc-500">QR Code Image</label>
          <div className="mt-2 flex items-start gap-4">
            {s.upi_qr_url ? (
              <img src={fileUrl(s.upi_qr_url) || s.upi_qr_url} alt="UPI QR" data-testid="upi-qr-preview" className="w-40 h-40 object-contain border border-zinc-200 p-2" />
            ) : (
              <div className="w-40 h-40 border border-dashed border-zinc-300 flex items-center justify-center text-xs text-zinc-400" data-testid="upi-qr-empty">
                No QR uploaded
              </div>
            )}
            <div className="flex flex-col gap-2">
              <label className="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold border border-zinc-300 hover:bg-zinc-100 cursor-pointer">
                <Upload className="w-3.5 h-3.5" />
                {uploading ? "Uploading…" : s.upi_qr_url ? "Replace QR" : "Upload QR image"}
                <input type="file" data-testid="upi-qr-file" accept=".png,.jpg,.jpeg,.webp" className="hidden" onChange={(e) => handleQrUpload(e.target.files?.[0])} />
              </label>
              {s.upi_qr_url && (
                <button onClick={clearQr} disabled={saving} data-testid="upi-qr-remove" className="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold border border-zinc-300 text-red-600 hover:bg-red-50">
                  <Trash2 className="w-3.5 h-3.5" /> Remove
                </button>
              )}
            </div>
          </div>
          <p className="text-xs text-zinc-500 mt-3">If both QR image and VPA are set, students see the image. If only VPA is set, they see the VPA to paste into their UPI app.</p>
        </div>
      </section>
    </div>
  );
}
