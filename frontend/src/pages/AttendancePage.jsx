import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "@/lib/api";
import { ArrowLeft, UserCheck } from "lucide-react";
import dayjs from "dayjs";

export default function AttendancePage() {
  const { id } = useParams();
  const [live, setLive] = useState(null);
  const [rows, setRows] = useState([]);

  useEffect(() => {
    api.get(`/live-classes/${id}`).then((r) => setLive(r.data));
    api.get(`/live-classes/${id}/attendance`).then((r) => setRows(r.data));
  }, [id]);

  return (
    <div className="max-w-3xl space-y-4" data-testid="attendance-page">
      <Link to="/app/live" className="inline-flex items-center gap-1.5 text-sm text-zinc-500 hover:text-zinc-950">
        <ArrowLeft className="w-4 h-4" /> Back to live classes
      </Link>
      <div>
        <p className="text-xs uppercase tracking-[0.2em] font-semibold text-zinc-400">Attendance</p>
        <h1 className="font-heading text-3xl font-black tracking-tight mt-1">{live?.title || "Loading…"}</h1>
        {live && <p className="text-xs text-zinc-500 mt-1">{dayjs(live.start_time).format("D MMM YYYY · h:mm A")} — {live.duration_min} min</p>}
      </div>

      <div className="border border-zinc-200">
        <div className="px-5 py-3 bg-zinc-50 border-b border-zinc-200 flex items-center gap-2">
          <UserCheck className="w-4 h-4 text-blue-700" />
          <span className="font-heading font-bold text-sm">{rows.length} student{rows.length !== 1 ? "s" : ""} marked present</span>
        </div>
        {rows.length === 0 ? (
          <p className="px-5 py-8 text-sm text-zinc-500 text-center" data-testid="attendance-empty">No students joined yet.</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-zinc-50 text-left text-xs uppercase tracking-[0.1em] text-zinc-500">
              <tr>
                <th className="px-5 py-2.5 font-semibold">#</th>
                <th className="px-5 py-2.5 font-semibold">Student</th>
                <th className="px-5 py-2.5 font-semibold">Joined at</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={r.student_id} className="border-t border-zinc-100" data-testid={`attendance-row-${r.student_id}`}>
                  <td className="px-5 py-2.5 text-zinc-400">{i + 1}</td>
                  <td className="px-5 py-2.5 font-medium">{r.student_name}</td>
                  <td className="px-5 py-2.5 text-zinc-500">{dayjs(r.attended_at).format("D MMM, h:mm A")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
