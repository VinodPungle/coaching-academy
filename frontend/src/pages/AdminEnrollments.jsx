import { useEffect, useState } from "react";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Search, Plus, Users, IndianRupee } from "lucide-react";
import dayjs from "dayjs";

export default function AdminEnrollments() {
  const [students, setStudents] = useState([]);
  const [courses, setCourses] = useState([]);
  const [q, setQ] = useState("");
  const [selectedStudent, setSelectedStudent] = useState("");
  const [selectedCourse, setSelectedCourse] = useState("");
  const [detail, setDetail] = useState(null);
  const [recordForm, setRecordForm] = useState({ amount: "", method: "upi", notes: "", grant_access: true });

  useEffect(() => {
    api.get("/admin/users?role=student").then((r) => setStudents(r.data));
    api.get("/admin/teachers").then(async () => {
      // fetch all courses via public list
      const r = await api.get("/courses");
      setCourses(r.data);
    });
  }, []);

  useEffect(() => {
    if (!selectedStudent || !selectedCourse) { setDetail(null); return; }
    api.get(`/admin/students/${selectedStudent}/course-payments/${selectedCourse}`)
      .then((r) => setDetail(r.data)).catch(() => setDetail(null));
  }, [selectedStudent, selectedCourse]);

  const filteredStudents = students.filter((s) =>
    !q.trim() || s.name.toLowerCase().includes(q.toLowerCase()) || s.email.toLowerCase().includes(q.toLowerCase())
  );

  const grant = async () => {
    if (!selectedStudent || !selectedCourse) return;
    try {
      await api.post("/admin/enrollments/grant", { student_id: selectedStudent, course_id: selectedCourse });
      toast.success("Access granted");
      setDetail(null);
      const r = await api.get(`/admin/students/${selectedStudent}/course-payments/${selectedCourse}`);
      setDetail(r.data);
    } catch (err) { toast.error(formatApiError(err)); }
  };

  const record = async () => {
    if (!recordForm.amount || Number(recordForm.amount) < 0) return toast.error("Enter a valid amount");
    try {
      await api.post("/admin/payments/record", {
        student_id: selectedStudent,
        course_id: selectedCourse,
        amount: Number(recordForm.amount),
        method: recordForm.method,
        notes: recordForm.notes,
        grant_access: recordForm.grant_access,
      });
      toast.success("Payment recorded");
      setRecordForm({ amount: "", method: "upi", notes: "", grant_access: true });
      const r = await api.get(`/admin/students/${selectedStudent}/course-payments/${selectedCourse}`);
      setDetail(r.data);
    } catch (err) { toast.error(formatApiError(err)); }
  };

  const edit = async (pid, current) => {
    const raw = window.prompt("New amount (₹):", current);
    if (raw === null) return;
    const amount = Number(raw);
    if (isNaN(amount) || amount < 0) return toast.error("Invalid amount");
    try {
      await api.put(`/admin/payments/${pid}`, { amount });
      const r = await api.get(`/admin/students/${selectedStudent}/course-payments/${selectedCourse}`);
      setDetail(r.data);
      toast.success("Payment updated");
    } catch (err) { toast.error(formatApiError(err)); }
  };

  const remove = async (pid) => {
    if (!window.confirm("Delete this payment record?")) return;
    try {
      await api.delete(`/admin/payments/${pid}`);
      const r = await api.get(`/admin/students/${selectedStudent}/course-payments/${selectedCourse}`);
      setDetail(r.data);
      toast.success("Payment removed");
    } catch (err) { toast.error(formatApiError(err)); }
  };

  return (
    <div className="space-y-6" data-testid="admin-enrollments-page">
      <div>
        <p className="text-xs uppercase tracking-[0.2em] font-semibold text-red-600">Admin Panel</p>
        <h1 className="font-heading text-3xl font-black tracking-tight mt-1">Enrollments & Payments</h1>
        <p className="text-sm text-zinc-500 mt-2">Grant course access manually and record UPI / offline payments.</p>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <div className="border border-zinc-200">
          <div className="px-4 py-3 border-b border-zinc-200 bg-zinc-50 flex items-center gap-2"><Users className="w-4 h-4 text-blue-700" /><h3 className="font-heading font-bold text-sm">Student</h3></div>
          <div className="p-3">
            <div className="relative">
              <Search className="absolute left-2.5 top-2.5 w-4 h-4 text-zinc-400" />
              <input data-testid="student-search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search students…" className="w-full border border-zinc-300 pl-8 pr-3 py-2 text-sm" />
            </div>
            <ul className="mt-2 max-h-56 overflow-auto">
              {filteredStudents.map((s) => (
                <li key={s.id}>
                  <button
                    onClick={() => setSelectedStudent(s.id)}
                    data-testid={`select-student-${s.id}`}
                    className={`w-full text-left px-3 py-2 text-sm border-b border-zinc-100 hover:bg-zinc-50 ${selectedStudent === s.id ? "bg-blue-50 border-blue-200" : ""}`}
                  >
                    <div className="font-medium">{s.name}</div>
                    <div className="text-xs text-zinc-500">{s.email}</div>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div className="border border-zinc-200">
          <div className="px-4 py-3 border-b border-zinc-200 bg-zinc-50 flex items-center gap-2"><IndianRupee className="w-4 h-4 text-blue-700" /><h3 className="font-heading font-bold text-sm">Course</h3></div>
          <div className="p-3">
            <select data-testid="course-select" value={selectedCourse} onChange={(e) => setSelectedCourse(e.target.value)} className="w-full border border-zinc-300 px-3 py-2 text-sm bg-white">
              <option value="">Choose a course…</option>
              {courses.map((c) => <option key={c.id} value={c.id}>{c.title} · ₹{c.price}</option>)}
            </select>
          </div>
        </div>
      </div>

      {detail && (
        <div className="border border-zinc-200 p-5 space-y-5" data-testid="enrollment-detail">
          <div className="grid sm:grid-cols-4 gap-4">
            <Stat label="Course fee" value={`₹${detail.fee}`} />
            <Stat label="Paid" value={`₹${detail.paid}`} color="text-green-700" />
            <Stat label="Outstanding" value={`₹${detail.outstanding}`} color={detail.outstanding > 0 ? "text-red-600" : "text-zinc-500"} />
            <Stat label="Access" value={detail.enrolled ? "Granted" : "Not granted"} />
          </div>

          {!detail.enrolled && (
            <button onClick={grant} data-testid="grant-access-button" className="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold bg-zinc-950 text-white hover:bg-zinc-800">
              <Plus className="w-3.5 h-3.5" /> Grant course access
            </button>
          )}

          <div className="border-t border-zinc-100 pt-4">
            <h4 className="font-heading font-bold text-sm mb-3">Record a payment</h4>
            <div className="grid sm:grid-cols-4 gap-2">
              <input data-testid="record-amount" type="number" min="0" placeholder="Amount ₹" value={recordForm.amount} onChange={(e) => setRecordForm({ ...recordForm, amount: e.target.value })} className="border border-zinc-300 px-3 py-2 text-sm" />
              <select data-testid="record-method" value={recordForm.method} onChange={(e) => setRecordForm({ ...recordForm, method: e.target.value })} className="border border-zinc-300 px-3 py-2 text-sm bg-white">
                <option value="upi">UPI</option><option value="cash">Cash</option><option value="bank">Bank transfer</option><option value="other">Other</option>
              </select>
              <input data-testid="record-notes" placeholder="Notes (optional)" value={recordForm.notes} onChange={(e) => setRecordForm({ ...recordForm, notes: e.target.value })} className="border border-zinc-300 px-3 py-2 text-sm" />
              <button onClick={record} data-testid="record-payment-button" className="px-4 py-2 text-sm font-semibold bg-blue-700 text-white hover:bg-blue-900">Record</button>
            </div>
            <label className="mt-2 flex items-center gap-2 text-xs cursor-pointer">
              <input type="checkbox" checked={recordForm.grant_access} onChange={(e) => setRecordForm({ ...recordForm, grant_access: e.target.checked })} className="accent-blue-700" />
              <span>Also grant course access</span>
            </label>
          </div>

          {detail.payments.length > 0 && (
            <div className="border-t border-zinc-100 pt-4">
              <h4 className="font-heading font-bold text-sm mb-3">Payment history</h4>
              <table className="w-full text-sm">
                <thead className="text-left text-xs uppercase tracking-[0.1em] text-zinc-500">
                  <tr><th className="py-1.5">Amount</th><th>Method</th><th>Notes</th><th>Recorded</th><th></th></tr>
                </thead>
                <tbody>
                  {detail.payments.map((p) => (
                    <tr key={p.id} className="border-t border-zinc-100" data-testid={`payment-row-${p.id}`}>
                      <td className="py-2 font-semibold">₹{p.amount}</td>
                      <td className="py-2 text-zinc-500 uppercase text-xs">{p.method}</td>
                      <td className="py-2 text-zinc-500">{p.notes || "—"}</td>
                      <td className="py-2 text-zinc-500 text-xs">{dayjs(p.created_at).format("D MMM, h:mm A")}</td>
                      <td className="py-2 text-right">
                        <button onClick={() => edit(p.id, p.amount)} data-testid={`edit-payment-${p.id}`} className="text-xs text-blue-700 hover:underline mr-3">Edit</button>
                        <button onClick={() => remove(p.id)} data-testid={`delete-payment-${p.id}`} className="text-xs text-red-600 hover:underline">Delete</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function Stat({ label, value, color = "text-zinc-950" }) {
  return (
    <div>
      <p className="text-xs uppercase tracking-[0.15em] font-semibold text-zinc-500">{label}</p>
      <p className={`font-heading text-xl font-black mt-1 ${color}`}>{value}</p>
    </div>
  );
}
