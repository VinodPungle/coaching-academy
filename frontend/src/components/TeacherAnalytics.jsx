// Teacher's per-course/per-test/per-assignment charts, rendered inside
// Dashboard.jsx for teacher/admin users. Data comes from a single call to
// GET /dashboard/teacher/analytics (backend/routers/dashboard.py), which
// already does the aggregation — this component only shapes it for recharts.
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, Legend,
} from "recharts";

// Truncate long titles so chart x-axis labels don't overlap.
const short = (s) => (s.length > 18 ? s.slice(0, 16) + "…" : s);

export const TeacherAnalytics = () => {
  const [data, setData] = useState(null);

  useEffect(() => {
    api.get("/dashboard/teacher/analytics").then((r) => setData(r.data));
  }, []);

  if (!data) return null;

  const courseData = data.courses.map((c) => ({ name: short(c.title), Students: c.students }));
  const testData = data.tests.map((t) => ({ name: short(t.title), "Avg %": t.avg_pct, Attempts: t.attempts }));
  const assignmentData = data.assignments.map((a) => ({ name: short(a.title), Graded: a.graded, Pending: a.pending }));

  return (
    <div className="space-y-6" data-testid="teacher-analytics">
      <h2 className="font-heading text-xl font-bold">Analytics</h2>
      <div className="grid lg:grid-cols-2 gap-6">
        <div className="border border-zinc-200 p-5" data-testid="chart-enrollments">
          <p className="text-xs uppercase tracking-[0.15em] font-semibold text-zinc-500 mb-4">Enrollments per course</p>
          {courseData.length === 0 ? (
            <p className="text-sm text-zinc-400 py-8">No courses yet.</p>
          ) : (
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={courseData} margin={{ top: 4, right: 8, left: -24, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e4e4e7" vertical={false} />
                <XAxis dataKey="name" tick={{ fontSize: 10 }} interval={0} angle={-12} height={44} />
                <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                <Tooltip cursor={{ fill: "#f4f4f5" }} contentStyle={{ fontSize: 12, borderRadius: 0 }} />
                <Bar dataKey="Students" fill="#1d4ed8" maxBarSize={44} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        <div className="border border-zinc-200 p-5" data-testid="chart-test-performance">
          <p className="text-xs uppercase tracking-[0.15em] font-semibold text-zinc-500 mb-4">Test performance</p>
          {testData.length === 0 ? (
            <p className="text-sm text-zinc-400 py-8">No tests yet.</p>
          ) : (
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={testData} margin={{ top: 4, right: 8, left: -24, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e4e4e7" vertical={false} />
                <XAxis dataKey="name" tick={{ fontSize: 10 }} interval={0} angle={-12} height={44} />
                <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                <Tooltip cursor={{ fill: "#f4f4f5" }} contentStyle={{ fontSize: 12, borderRadius: 0 }} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Bar dataKey="Avg %" fill="#1d4ed8" maxBarSize={36} />
                <Bar dataKey="Attempts" fill="#e63946" maxBarSize={36} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        <div className="border border-zinc-200 p-5 lg:col-span-2" data-testid="chart-assignments">
          <p className="text-xs uppercase tracking-[0.15em] font-semibold text-zinc-500 mb-4">Assignment grading status</p>
          {assignmentData.length === 0 ? (
            <p className="text-sm text-zinc-400 py-8">No assignments yet.</p>
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={assignmentData} margin={{ top: 4, right: 8, left: -24, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e4e4e7" vertical={false} />
                <XAxis dataKey="name" tick={{ fontSize: 10 }} interval={0} />
                <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                <Tooltip cursor={{ fill: "#f4f4f5" }} contentStyle={{ fontSize: 12, borderRadius: 0 }} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Bar dataKey="Graded" stackId="a" fill="#16a34a" maxBarSize={44} />
                <Bar dataKey="Pending" stackId="a" fill="#e63946" maxBarSize={44} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>
    </div>
  );
};
