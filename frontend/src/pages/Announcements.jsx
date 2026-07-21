// Announcements feed ("/app/announcements") — teachers/admins post (global
// or course-scoped); students see global posts plus ones for courses
// they're enrolled in. Visibility filtering happens server-side (see
// list_announcements in backend/routers/announcements.py); this page just
// renders whatever the API returns.
import { useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Megaphone, Plus, Trash2 } from "lucide-react";
import dayjs from "dayjs";

export default function AnnouncementsPage() {
  const { user } = useAuth();
  const [items, setItems] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ title: "", body: "", course_id: "" });
  const [teacherCourses, setTeacherCourses] = useState([]);

  const isTeacher = user.role !== "student";
  const load = () => api.get("/announcements").then((r) => setItems(r.data));
  useEffect(() => {
    load();
    if (user.role === "teacher") {
      api.get("/teacher/courses").then((r) => setTeacherCourses(r.data)).catch(() => {});
    }
  }, [user.role]);

  const create = async (e) => {
    e.preventDefault();
    try {
      await api.post("/announcements", { ...form, course_id: form.course_id || null });
      toast.success("Announcement posted");
      setShowForm(false);
      setForm({ title: "", body: "", course_id: "" });
      load();
    } catch (err) {
      toast.error(formatApiError(err));
    }
  };

  const remove = async (id) => {
    try {
      await api.delete(`/announcements/${id}`);
      toast.success("Announcement deleted");
      load();
    } catch (err) {
      toast.error(formatApiError(err));
    }
  };

  const canDelete = (a) => user.role === "admin" || a.teacher_id === user.id;

  return (
    <div className="space-y-6 max-w-3xl">
      <div className="flex items-end justify-between flex-wrap gap-4">
        <h1 className="font-heading text-3xl font-black tracking-tight">Announcements</h1>
        {isTeacher && (
          <button onClick={() => setShowForm(!showForm)} data-testid="new-announcement-button" className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-semibold bg-blue-700 text-white hover:bg-blue-900 transition-colors">
            <Plus className="w-4 h-4" /> Post announcement
          </button>
        )}
      </div>

      {isTeacher && showForm && (
        <form onSubmit={create} className="border border-zinc-200 p-6 space-y-4" data-testid="new-announcement-form">
          <div>
            <label className="text-xs uppercase tracking-[0.15em] font-semibold text-zinc-500">Title</label>
            <input data-testid="announcement-title-input" required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} className="mt-1 w-full border border-zinc-300 px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="text-xs uppercase tracking-[0.15em] font-semibold text-zinc-500">Message</label>
            <textarea data-testid="announcement-body-input" required value={form.body} onChange={(e) => setForm({ ...form, body: e.target.value })} rows={3} className="mt-1 w-full border border-zinc-300 px-3 py-2 text-sm" />
          </div>
          {user.role === "teacher" && (
            <div>
              <label className="text-xs uppercase tracking-[0.15em] font-semibold text-zinc-500">Course (optional)</label>
              <select data-testid="announcement-course-select" value={form.course_id} onChange={(e) => setForm({ ...form, course_id: e.target.value })} className="mt-1 w-full border border-zinc-300 px-3 py-2 text-sm bg-white">
                <option value="">All students</option>
                {teacherCourses.map((c) => <option key={c.id} value={c.id}>{c.title}</option>)}
              </select>
            </div>
          )}
          <div className="flex gap-2">
            <button data-testid="announcement-submit-button" className="px-5 py-2 text-sm font-semibold bg-blue-700 text-white hover:bg-blue-900">Post</button>
            <button type="button" onClick={() => setShowForm(false)} className="px-5 py-2 text-sm font-semibold border border-zinc-300 hover:bg-zinc-100">Cancel</button>
          </div>
        </form>
      )}

      <div className="space-y-3">
        {items.length === 0 && <p className="text-sm text-zinc-500" data-testid="announcements-empty-state">No announcements yet.</p>}
        {items.map((a) => (
          <div key={a.id} className="border border-zinc-200 p-5 flex gap-4" data-testid={`announcement-${a.id}`}>
            <div className="shrink-0 w-10 h-10 bg-zinc-100 flex items-center justify-center">
              <Megaphone className="w-4 h-4 text-red-600" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <h3 className="font-heading font-bold">{a.title}</h3>
                {a.course_name ? (
                  <span className="text-[10px] uppercase tracking-[0.1em] font-bold bg-zinc-950 text-white px-1.5 py-0.5" data-testid={`announcement-course-badge-${a.id}`}>{a.course_name}</span>
                ) : (
                  <span className="text-[10px] uppercase tracking-[0.1em] font-bold bg-blue-50 text-blue-700 border border-blue-200 px-1.5 py-0.5" data-testid={`announcement-all-badge-${a.id}`}>For all students</span>
                )}
              </div>
              <p className="text-sm text-zinc-600 mt-1 leading-relaxed">{a.body}</p>
              <p className="text-xs text-zinc-400 mt-2">{a.teacher_name} · {dayjs(a.created_at).format("D MMM YYYY, h:mm A")}</p>
            </div>
            {isTeacher && canDelete(a) && (
              <button onClick={() => remove(a.id)} data-testid={`delete-announcement-${a.id}`} className="shrink-0 p-2 h-fit border border-zinc-300 text-zinc-500 hover:text-red-600 hover:border-red-300 transition-colors">
                <Trash2 className="w-4 h-4" />
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
