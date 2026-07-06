import { useEffect, useState } from "react";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { X, CreditCard, Smartphone, ShieldCheck, Users } from "lucide-react";

export default function EnrollModal({ course, onClose, onSuccess }) {
  const [config, setConfig] = useState(null);
  const [batches, setBatches] = useState([]);
  const [batchId, setBatchId] = useState("");
  const [method, setMethod] = useState("stripe");
  const [busy, setBusy] = useState(false);

  const isFree = !course.price;

  useEffect(() => {
    api.get("/payments/config").then((r) => setConfig(r.data));
    api.get(`/courses/${course.id}/batches`).then((r) => setBatches(r.data));
  }, [course.id]);

  const pay = async () => {
    setBusy(true);
    try {
      if (isFree) {
        await api.post(`/courses/${course.id}/enroll`, { batch_id: batchId || null });
      } else {
        const { data } = await api.post("/payments/checkout", {
          course_id: course.id,
          batch_id: batchId || null,
          method,
        });
        await api.post(`/payments/${data.payment.id}/confirm`);
      }
      toast.success(isFree ? "Enrolled successfully" : "Payment successful — you are enrolled!");
      onSuccess();
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-zinc-950/50 p-4" data-testid="enroll-modal">
      <div className="w-full max-w-md bg-white border border-zinc-200 max-h-[90vh] overflow-y-auto">
        <div className="flex items-start justify-between px-6 py-4 border-b border-zinc-200">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] font-semibold text-zinc-500">Enroll in</p>
            <h2 className="font-heading font-bold mt-0.5">{course.title}</h2>
          </div>
          <button onClick={onClose} data-testid="enroll-modal-close" className="p-1 text-zinc-400 hover:text-zinc-950">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="px-6 py-5 space-y-5">
          {batches.length > 0 && (
            <div>
              <p className="text-xs uppercase tracking-[0.15em] font-semibold text-zinc-500 mb-2">Choose your batch</p>
              <div className="space-y-2">
                {batches.map((b) => {
                  const full = b.capacity && b.enrolled_count >= b.capacity;
                  return (
                    <label
                      key={b.id}
                      data-testid={`batch-option-${b.id}`}
                      className={`flex items-center gap-3 border px-4 py-3 text-sm transition-colors ${
                        full ? "opacity-50 cursor-not-allowed" : "cursor-pointer"
                      } ${batchId === b.id ? "border-blue-700 bg-blue-50" : "border-zinc-200 hover:bg-zinc-50"}`}
                    >
                      <input type="radio" name="batch" disabled={full} checked={batchId === b.id} onChange={() => setBatchId(b.id)} className="accent-blue-700" />
                      <div className="flex-1 min-w-0">
                        <span className="font-semibold">{b.name}</span>
                        <p className="text-xs text-zinc-500 mt-0.5">{b.schedule}{b.start_date ? ` · starts ${b.start_date}` : ""}</p>
                      </div>
                      <span className="text-xs text-zinc-400 inline-flex items-center gap-1 shrink-0">
                        <Users className="w-3.5 h-3.5" />{b.enrolled_count}{b.capacity ? `/${b.capacity}` : ""}
                      </span>
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

          {!isFree && (
            <div>
              <p className="text-xs uppercase tracking-[0.15em] font-semibold text-zinc-500 mb-2">Payment method</p>
              <div className="grid grid-cols-2 gap-px bg-zinc-200 border border-zinc-200">
                <button
                  type="button"
                  data-testid="method-stripe"
                  onClick={() => setMethod("stripe")}
                  className={`flex items-center justify-center gap-2 py-3 text-sm font-semibold transition-colors ${method === "stripe" ? "bg-blue-700 text-white" : "bg-white text-zinc-500 hover:bg-zinc-50"}`}
                >
                  <CreditCard className="w-4 h-4" /> Card (Stripe)
                </button>
                <button
                  type="button"
                  data-testid="method-razorpay"
                  onClick={() => setMethod("razorpay")}
                  className={`flex items-center justify-center gap-2 py-3 text-sm font-semibold transition-colors ${method === "razorpay" ? "bg-blue-700 text-white" : "bg-white text-zinc-500 hover:bg-zinc-50"}`}
                >
                  <Smartphone className="w-4 h-4" /> UPI (Razorpay)
                </button>
              </div>
              {config?.demo_mode && (
                <p className="mt-2 text-xs text-amber-700 bg-amber-50 border border-amber-200 px-3 py-2" data-testid="demo-mode-notice">
                  Demo mode — payment gateway keys are not configured yet. This checkout will simulate a successful payment.
                </p>
              )}
            </div>
          )}

          <div className="border-t border-zinc-200 pt-4 flex items-center justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.15em] font-semibold text-zinc-500">Total</p>
              <p className="font-heading text-2xl font-black" data-testid="enroll-total">{isFree ? "Free" : `₹${course.price}`}</p>
            </div>
            <button
              onClick={pay}
              disabled={busy}
              data-testid="pay-enroll-button"
              className="inline-flex items-center gap-2 px-6 py-3 font-semibold bg-blue-700 text-white hover:bg-blue-900 transition-colors disabled:opacity-50"
            >
              <ShieldCheck className="w-4 h-4" />
              {busy ? "Processing…" : isFree ? "Enroll free" : `Pay ₹${course.price}`}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
