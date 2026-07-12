import { useEffect, useState } from "react";
import { api, formatApiError, fileUrl } from "@/lib/api";
import { toast } from "sonner";
import { X, Users, ShieldCheck, Copy, ExternalLink } from "lucide-react";

/**
 * Phase 7 Enrol modal:
 * - Free course OR portal in demo mode → one-click enrol (no payment step)
 * - Paid course in live mode → shows UPI QR / VPA and asks the student to contact admin after paying
 */
export default function EnrollModal({ course, batches: batchesProp, onClose, onSuccess, onDone }) {
  const [settings, setSettings] = useState(null);
  const [batches, setBatches] = useState(batchesProp || []);
  const [batchId, setBatchId] = useState("");
  const [busy, setBusy] = useState(false);
  const [vpaCopied, setVpaCopied] = useState(false);

  const isFree = Boolean(course.is_free) || !course.price;

  useEffect(() => {
    api.get("/settings/public").then((r) => setSettings(r.data)).catch(() => setSettings({ portal_mode: "live", upi_qr_url: "", upi_vpa: "" }));
    if (!batchesProp) api.get(`/courses/${course.id}/batches`).then((r) => setBatches(r.data));
  }, [course.id, batchesProp]);

  const isDemoMode = settings?.portal_mode === "demo";
  const enrolFreely = isFree || isDemoMode;

  const enrol = async () => {
    setBusy(true);
    try {
      await api.post(`/courses/${course.id}/enroll`, { batch_id: batchId || null });
      toast.success("Enrolled successfully");
      (onSuccess || onDone)?.();
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setBusy(false);
    }
  };

  const copyVpa = async () => {
    if (!settings?.upi_vpa) return;
    try {
      await navigator.clipboard.writeText(settings.upi_vpa);
      setVpaCopied(true);
      setTimeout(() => setVpaCopied(false), 2000);
    } catch { /* clipboard blocked */ }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-zinc-950/50 p-4" data-testid="enroll-modal">
      <div className="w-full max-w-md bg-white border border-zinc-200 max-h-[90vh] overflow-y-auto">
        <div className="flex items-start justify-between px-6 py-4 border-b border-zinc-200">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] font-semibold text-zinc-500">Enroll in</p>
            <h2 className="font-heading font-bold mt-0.5">{course.title}</h2>
          </div>
          <button onClick={onClose} data-testid="enroll-modal-close" className="p-1 text-zinc-400 hover:text-zinc-950"><X className="w-5 h-5" /></button>
        </div>

        <div className="px-6 py-5 space-y-5">
          {batches.length > 0 && (
            <div>
              <p className="text-xs uppercase tracking-[0.15em] font-semibold text-zinc-500 mb-2">Choose your batch</p>
              <div className="space-y-2">
                {batches.map((b) => {
                  const full = b.capacity && b.enrolled_count >= b.capacity;
                  return (
                    <label key={b.id} data-testid={`batch-option-${b.id}`} className={`flex items-center gap-3 border px-4 py-3 text-sm transition-colors ${full ? "opacity-50 cursor-not-allowed" : "cursor-pointer"} ${batchId === b.id ? "border-blue-700 bg-blue-50" : "border-zinc-200 hover:bg-zinc-50"}`}>
                      <input type="radio" name="batch" disabled={full} checked={batchId === b.id} onChange={() => setBatchId(b.id)} className="accent-blue-700" />
                      <div className="flex-1 min-w-0">
                        <span className="font-semibold">{b.name}</span>
                        <p className="text-xs text-zinc-500 mt-0.5">{b.schedule}{b.start_date ? ` · starts ${b.start_date}` : ""}</p>
                      </div>
                      <span className="text-xs text-zinc-400 inline-flex items-center gap-1 shrink-0"><Users className="w-3.5 h-3.5" />{b.enrolled_count}{b.capacity ? `/${b.capacity}` : ""}</span>
                    </label>
                  );
                })}
                <label className={`flex items-center gap-3 border px-4 py-3 text-sm cursor-pointer transition-colors ${batchId === "" ? "border-blue-700 bg-blue-50" : "border-zinc-200 hover:bg-zinc-50"}`}>
                  <input type="radio" name="batch" checked={batchId === ""} onChange={() => setBatchId("")} className="accent-blue-700" data-testid="batch-option-none" />
                  <span className="text-zinc-500">Self-paced (no batch)</span>
                </label>
              </div>
            </div>
          )}

          {enrolFreely ? (
            <div className="border-t border-zinc-200 pt-4 flex items-center justify-between">
              <div>
                <p className="text-xs uppercase tracking-[0.15em] font-semibold text-zinc-500">Total</p>
                <p className="font-heading text-2xl font-black" data-testid="enroll-total">
                  {isFree ? "Free" : "Free (Demo mode)"}
                </p>
                {isDemoMode && !isFree && <p className="text-xs text-amber-700 mt-1">Portal is in Demo mode — normal fee ₹{course.price} waived.</p>}
              </div>
              <button onClick={enrol} disabled={busy} data-testid="pay-enroll-button" className="inline-flex items-center gap-2 px-6 py-3 font-semibold bg-blue-700 text-white hover:bg-blue-900 transition-colors disabled:opacity-50">
                <ShieldCheck className="w-4 h-4" /> {busy ? "Enrolling…" : "Enrol now"}
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="border-t border-zinc-200 pt-4">
                <p className="text-xs uppercase tracking-[0.15em] font-semibold text-zinc-500">Course fee</p>
                <p className="font-heading text-3xl font-black">₹{course.price}</p>
              </div>

              <div className="border border-zinc-200 p-4 space-y-3" data-testid="upi-payment-panel">
                <p className="text-xs uppercase tracking-[0.15em] font-semibold text-zinc-500">Pay via UPI</p>
                {settings?.upi_qr_url ? (
                  <img src={fileUrl(settings.upi_qr_url) || settings.upi_qr_url} alt="UPI QR" className="w-40 h-40 mx-auto object-contain border border-zinc-200 p-2" data-testid="upi-qr-image" />
                ) : settings?.upi_vpa ? (
                  <div className="w-40 h-40 mx-auto flex items-center justify-center border border-zinc-200 bg-zinc-50 text-xs text-zinc-500 text-center p-4" data-testid="upi-qr-placeholder">
                    QR not uploaded — use VPA below in your UPI app
                  </div>
                ) : (
                  <p className="text-sm text-amber-700 bg-amber-50 border border-amber-200 px-3 py-2" data-testid="upi-not-configured">
                    UPI not configured yet. Please contact the admin.
                  </p>
                )}
                {settings?.upi_vpa && (
                  <button onClick={copyVpa} data-testid="upi-vpa-copy" className="w-full inline-flex items-center justify-center gap-2 px-3 py-2 text-sm font-semibold border border-zinc-300 hover:bg-zinc-100">
                    <Copy className="w-3.5 h-3.5" />
                    {vpaCopied ? "Copied!" : settings.upi_vpa}
                  </button>
                )}
                <p className="text-xs text-zinc-500 leading-relaxed">
                  After paying, share the payment screenshot with the admin. Your access will be granted within 24 hours.
                </p>
                <a href="mailto:admin@rgpacademy.com?subject=UPI payment sent" data-testid="upi-contact-admin" className="w-full block text-center px-3 py-2 text-sm font-semibold bg-zinc-950 text-white hover:bg-zinc-800 inline-flex items-center justify-center gap-1">
                  Notify admin <ExternalLink className="w-3.5 h-3.5" />
                </a>
              </div>

              <button onClick={onClose} className="w-full px-4 py-2 text-sm font-semibold border border-zinc-300 hover:bg-zinc-100">Close</button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
