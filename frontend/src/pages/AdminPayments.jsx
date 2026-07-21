// Admin-only read-only payment ledger ("/app/payments") — every recorded
// payment (UPI/manual + Razorpay) with total revenue. To actually record
// or edit a payment for a specific student, see AdminEnrollments.jsx.
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { IndianRupee } from "lucide-react";
import dayjs from "dayjs";

const STATUS_STYLE = {
  paid: "bg-green-50 text-green-700 border-green-200",
  pending: "bg-amber-50 text-amber-700 border-amber-200",
  failed: "bg-red-50 text-red-600 border-red-200",
};

export default function AdminPayments() {
  const [data, setData] = useState(null);

  useEffect(() => {
    api.get("/admin/payments").then((r) => setData(r.data));
  }, []);

  if (!data) return <p className="text-sm text-zinc-500">Loading payments…</p>;

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between flex-wrap gap-4">
        <h1 className="font-heading text-3xl font-black tracking-tight">Payments</h1>
        <div className="border border-zinc-200 px-5 py-3 flex items-center gap-3">
          <IndianRupee className="w-5 h-5 text-green-600" />
          <div>
            <div className="font-heading text-xl font-black" data-testid="admin-total-revenue">₹{data.total_revenue}</div>
            <div className="text-[10px] uppercase tracking-[0.15em] text-zinc-500">Total revenue</div>
          </div>
        </div>
      </div>

      <div className="border border-zinc-200 overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-zinc-50 text-left text-xs uppercase tracking-[0.1em] text-zinc-500">
            <tr>
              <th className="px-5 py-3 font-semibold">Student</th>
              <th className="px-5 py-3 font-semibold">Course</th>
              <th className="px-5 py-3 font-semibold">Amount</th>
              <th className="px-5 py-3 font-semibold">Method</th>
              <th className="px-5 py-3 font-semibold">Status</th>
              <th className="px-5 py-3 font-semibold">Date</th>
            </tr>
          </thead>
          <tbody>
            {data.payments.map((p) => (
              <tr key={p.id} className="border-t border-zinc-100" data-testid={`admin-payment-row-${p.id}`}>
                <td className="px-5 py-3 font-medium">{p.student_name}</td>
                <td className="px-5 py-3 text-zinc-500 max-w-56 truncate">{p.course_title}</td>
                <td className="px-5 py-3 font-semibold">₹{p.amount}</td>
                <td className="px-5 py-3 text-zinc-500 capitalize">{p.method}{p.gateway === "demo" ? " (demo)" : ""}</td>
                <td className="px-5 py-3">
                  <span className={`text-[10px] uppercase tracking-[0.1em] font-bold border px-2 py-1 ${STATUS_STYLE[p.status] || ""}`}>{p.status}</span>
                </td>
                <td className="px-5 py-3 text-zinc-500">{dayjs(p.created_at).format("D MMM YYYY, h:mm A")}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {data.payments.length === 0 && <p className="px-5 py-8 text-sm text-zinc-500" data-testid="admin-payments-empty">No payments recorded yet.</p>}
      </div>
    </div>
  );
}
