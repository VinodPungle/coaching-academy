import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import { BookOpen, FileQuestion, BarChart3, ClipboardList, Users, Radio, Plus } from "lucide-react";
import { TeacherAnalytics } from "@/components/TeacherAnalytics";
import { AdminDashboard } from "@/components/AdminDashboard";
import dayjs from "dayjs";

function StatCard({ icon: Icon, label, value, testid }) {
  return (
    <div className="border border-zinc-200 bg-white p-6 hover:border-zinc-300 hover:shadow-sm transition-all" data-testid={testid}>
      <Icon className="w-5 h-5 text-blue-700" strokeWidth={1.5} />
      <div className="font-heading text-3xl font-black mt-3">{value}</div>
      <div className="text-xs uppercase tracking-[0.15em] text-zinc-500 mt-1">{label}</div>
    </div>
  );
}

function UpcomingClasses({ classes }) {
  return (
    <div className="border border-zinc-200">
      <div className="px-6 py-4 border-b border-zinc-200 flex items-center gap-2">
        <Radio className="w-4 h-4 text-red-600" />
        <h2 className="font-heading font-bold">Upcoming Live Classes</h2>
      </div>
      {classes.length === 0 ? (
        <p className="px-6 py-8 text-sm text-zinc-500">No upcoming classes scheduled.</p>
      ) : (
        classes.map((c) => (
          <div key={c.id} className="px-6 py-4 border-b border-zinc-100 last:border-0 flex items-center justify-between gap-4">
            <div>
              <div className="font-semibold text-sm">{c.title}</div>
              <div className="text-xs text-zinc-500 mt-0.5">
                {c.subject} · {dayjs(c.start_time).format("ddd, D MMM · h:mm A")} · {c.duration_min} min
              </div>
            </div>
            <Link to="/app/live" className="text-xs font-semibold text-blue-700 hover:underline shrink-0">
              Details
            </Link>
          </div>
        ))
      )}
    </div>
  );
}

export default function Dashboard() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const isAdmin = user.role === "admin";

  useEffect(() => {
    if (isAdmin) return;
    api.get(user.role === "student" ? "/dashboard/student" : "/dashboard/teacher").then((r) => setData(r.data));
  }, [user.role, isAdmin]);

  if (isAdmin) return <AdminDashboard user={user} />;
  if (!data) return <p className="text-sm text-zinc-500" data-testid="dashboard-loading">Loading dashboard…</p>;

  if (user.role === "student") {
    return (
      <div className="space-y-8" data-testid="student-dashboard">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] font-semibold text-zinc-500">Student Portal</p>
          <h1 className="font-heading text-3xl font-black tracking-tight mt-1">Hello, {user.name.split(" ")[0]}</h1>
        </div>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard icon={BookOpen} label="Enrolled courses" value={data.enrolled_courses} testid="stat-enrolled-courses" />
          <StatCard icon={FileQuestion} label="Tests attempted" value={data.tests_attempted} testid="stat-tests-attempted" />
          <StatCard icon={BarChart3} label="Average score" value={`${data.avg_score_pct}%`} testid="stat-avg-score" />
          <StatCard icon={ClipboardList} label="Pending assignments" value={data.pending_assignments} testid="stat-pending-assignments" />
        </div>
        <div className="grid lg:grid-cols-2 gap-6">
          <UpcomingClasses classes={data.upcoming_classes} />
          <div className="border border-zinc-200">
            <div className="px-6 py-4 border-b border-zinc-200">
              <h2 className="font-heading font-bold">Latest Announcements</h2>
            </div>
            {data.recent_announcements.map((a) => (
              <div key={a.id} className="px-6 py-4 border-b border-zinc-100 last:border-0">
                <div className="font-semibold text-sm">{a.title}</div>
                <p className="text-xs text-zinc-500 mt-1 line-clamp-2">{a.body}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8" data-testid="teacher-dashboard">
      <div className="flex items-end justify-between flex-wrap gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] font-semibold text-zinc-500">Teacher Portal</p>
          <h1 className="font-heading text-3xl font-black tracking-tight mt-1">Hello, {user.name.split(" ")[0]}</h1>
        </div>
        <div className="flex gap-2">
          <Link to="/app/tests/new" data-testid="quick-create-test" className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-semibold bg-blue-700 text-white hover:bg-blue-900 transition-colors">
            <Plus className="w-4 h-4" /> New test
          </Link>
          <Link to="/app/live" data-testid="quick-schedule-class" className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-semibold border border-zinc-300 hover:bg-zinc-100 transition-colors">
            <Radio className="w-4 h-4" /> Schedule class
          </Link>
        </div>
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={BookOpen} label="Courses" value={data.total_courses} testid="stat-total-courses" />
        <StatCard icon={Users} label="Enrolled students" value={data.total_students} testid="stat-total-students" />
        <StatCard icon={FileQuestion} label="Tests created" value={data.total_tests} testid="stat-total-tests" />
        <StatCard icon={BarChart3} label="Test attempts" value={data.total_attempts} testid="stat-total-attempts" />
      </div>
      <UpcomingClasses classes={data.upcoming_classes} />
      <TeacherAnalytics />
    </div>
  );
}
