// Admin's home page content — rendered inside Dashboard.jsx when
// user.role === "admin". Platform-wide stat cards + a recent-signups feed,
// backed by GET /admin/stats (backend/routers/admin.py).
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Users, GraduationCap, BookOpen, IndianRupee, FileQuestion, BarChart3 } from "lucide-react";
import dayjs from "dayjs";

export const AdminDashboard = ({ user }) => {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    api.get("/admin/stats").then((r) => setStats(r.data));
  }, []);

  if (!stats) return <p className="text-sm text-zinc-500" data-testid="admin-dashboard-loading">Loading admin dashboard…</p>;

  const CARDS = [
    [Users, "Students", stats.students],
    [GraduationCap, "Teachers", stats.teachers],
    [BookOpen, "Courses", stats.courses],
    [BarChart3, "Enrollments", stats.enrollments],
    [FileQuestion, "Test attempts", stats.attempts],
    [IndianRupee, "Revenue", `₹${stats.revenue}`],
  ];

  return (
    <div className="space-y-8" data-testid="admin-dashboard">
      <div>
        <p className="text-xs uppercase tracking-[0.2em] font-semibold text-red-600">Admin Panel</p>
        <h1 className="font-heading text-3xl font-black tracking-tight mt-1">Hello, {user.name.split(" ")[0]}</h1>
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
        {CARDS.map(([Icon, label, value]) => (
          <div key={label} className="border border-zinc-200 bg-white p-6 hover:border-zinc-300 hover:shadow-sm transition-all" data-testid={`admin-stat-${label.toLowerCase().replace(" ", "-")}`}>
            <Icon className="w-5 h-5 text-blue-700" strokeWidth={1.5} />
            <div className="font-heading text-3xl font-black mt-3">{value}</div>
            <div className="text-xs uppercase tracking-[0.15em] text-zinc-500 mt-1">{label}</div>
          </div>
        ))}
      </div>
      <div className="border border-zinc-200">
        <div className="px-6 py-4 border-b border-zinc-200">
          <h2 className="font-heading font-bold">Recent Signups</h2>
        </div>
        {stats.recent_users.map((u) => (
          <div key={u.id} className="px-6 py-3 border-b border-zinc-100 last:border-0 flex items-center justify-between gap-4">
            <div className="min-w-0">
              <span className="font-semibold text-sm">{u.name}</span>
              <span className="text-xs text-zinc-500 ml-2">{u.email}</span>
            </div>
            <div className="flex items-center gap-3 shrink-0">
              <span className="text-[10px] uppercase tracking-[0.15em] font-bold bg-zinc-100 px-2 py-1">{u.role}</span>
              <span className="text-xs text-zinc-400">{dayjs(u.created_at).format("D MMM")}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
