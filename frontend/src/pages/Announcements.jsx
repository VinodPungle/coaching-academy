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
  const [form, setForm] = useState({ title: "", body: "" });

  const isTeacher = user.role !== "student";
  const load = () => api.get("/announcements").then((r) => setItems(r.data));
  useEffect(() => { load(); }, []);

  const create = async (e) => {
    e.preventDefault();
    try {
      await api.post("/announcements", form);
      toast.success("Announcement posted");
      setShowForm(false);
      setForm({ title: "", body: "" });
      load();
    } catch (err) {
      toast.error(formatApiError(err));
    }
  };

  const remove = async (id) => {
    await api.delete(`/announcements/${id}`);
    toast.success("Announcement deleted");
    load();
  };

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
              <h3 className="font-heading font-bold">{a.title}</h3>
              <p className="text-sm text-zinc-600 mt-1 leading-relaxed">{a.body}</p>
              <p className="text-xs text-zinc-400 mt-2">{a.teacher_name} · {dayjs(a.created_at).format("D MMM YYYY, h:mm A")}</p>
            </div>
            {isTeacher && a.teacher_id === user.id && (
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
