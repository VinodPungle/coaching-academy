// Admin-only editor for ANY teacher's public profile ("/app/teacher-profiles")
// — a select-teacher-then-edit-their-bio UI. Compare with
// TeacherProfileEdit.jsx, the near-identical page a teacher uses to edit
// only their own profile (no teacher-picker there).
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Save, User } from "lucide-react";
import { api, formatApiError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import ProfilePhotoEditor from "@/components/ProfilePhotoEditor";

export default function AdminTeacherProfiles() {
  const { user } = useAuth();
  const [teachers, setTeachers] = useState([]);
  const [selectedId, setSelectedId] = useState("");
  const [form, setForm] = useState({ display_name: "", subtitle: "", bio: "", photo_url: "" });
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    api.get("/teacher-profiles")
      .then(({ data }) => {
        setTeachers(data || []);
        if (data && data.length && !selectedId) {
          setSelectedId(data[0].id);
        }
      })
      .catch((err) => toast.error(formatApiError(err)))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  useEffect(() => {
    const t = teachers.find((x) => x.id === selectedId);
    if (t) {
      setForm({
        display_name: t.display_name || t.name || "",
        subtitle: t.subtitle || "",
        bio: t.bio || "",
        photo_url: t.photo_url || "",
      });
    }
  }, [selectedId, teachers]);

  if (user?.role !== "admin") {
    return <p className="text-sm text-red-600" data-testid="teacher-profiles-forbidden">Admins only.</p>;
  }

  const save = async () => {
    if (!selectedId) return;
    setBusy(true);
    try {
      await api.put(`/teacher-profiles/${selectedId}`, form);
      toast.success("Teacher profile saved");
      load();
    } catch (err) { toast.error(formatApiError(err)); }
    finally { setBusy(false); }
  };

  return (
    <div className="space-y-6" data-testid="admin-teacher-profiles">
      <div>
        <h1 className="font-heading text-2xl sm:text-3xl font-black tracking-tight">Teacher profiles</h1>
        <p className="text-sm text-zinc-500 mt-1">Edit each teacher&apos;s public bio shown on the /teachers page. Teachers can also update their own bio from their portal.</p>
      </div>

      {loading ? <p className="text-sm text-zinc-500">Loading…</p> : teachers.length === 0 ? (
        <p className="text-sm text-zinc-500" data-testid="no-teachers">No teachers registered yet.</p>
      ) : (
        <div className="grid md:grid-cols-[260px_1fr] gap-6">
          <aside className="border border-zinc-200 divide-y divide-zinc-200 self-start" data-testid="teacher-profiles-list">
            {teachers.map((t) => (
              <button
                key={t.id}
                onClick={() => setSelectedId(t.id)}
                data-testid={`teacher-profile-item-${t.id}`}
                className={`w-full text-left px-4 py-3 flex items-center gap-3 transition-colors ${selectedId === t.id ? "bg-blue-700 text-white" : "hover:bg-zinc-50"}`}
              >
                <div className={`w-8 h-8 flex items-center justify-center rounded-full ${selectedId === t.id ? "bg-white/20" : "bg-zinc-100"}`}>
                  <User className={`w-4 h-4 ${selectedId === t.id ? "text-white" : "text-zinc-500"}`} />
                </div>
                <div className="min-w-0">
                  <div className="text-sm font-semibold truncate">{t.display_name || t.name}</div>
                  <div className={`text-xs truncate ${selectedId === t.id ? "text-white/80" : "text-zinc-500"}`}>{t.email}</div>
                </div>
              </button>
            ))}
          </aside>

          <section className="border border-zinc-200 p-5 md:p-6 space-y-4" data-testid="teacher-profile-editor">
            <div>
              <label className="text-xs uppercase tracking-[0.15em] font-semibold text-zinc-500">Profile photo</label>
              <div className="mt-2">
                <ProfilePhotoEditor value={form.photo_url} onChange={(v) => setForm({ ...form, photo_url: v })} testidPrefix="admin-teacher-photo" />
              </div>
            </div>
            <div>
              <label className="text-xs uppercase tracking-[0.15em] font-semibold text-zinc-500">Display name</label>
              <input
                data-testid="profile-display-name-input"
                value={form.display_name}
                maxLength={200}
                onChange={(e) => setForm({ ...form, display_name: e.target.value })}
                className="mt-1.5 w-full border border-zinc-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-700"
              />
            </div>
            <div>
              <label className="text-xs uppercase tracking-[0.15em] font-semibold text-zinc-500">Subtitle (e.g. subject / credentials)</label>
              <input
                data-testid="profile-subtitle-input"
                value={form.subtitle}
                maxLength={300}
                onChange={(e) => setForm({ ...form, subtitle: e.target.value })}
                className="mt-1.5 w-full border border-zinc-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-700"
              />
            </div>
            <div>
              <label className="text-xs uppercase tracking-[0.15em] font-semibold text-zinc-500">Bio</label>
              <textarea
                data-testid="profile-bio-input"
                value={form.bio}
                maxLength={5000}
                rows={12}
                onChange={(e) => setForm({ ...form, bio: e.target.value })}
                className="mt-1.5 w-full border border-zinc-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-700 resize-none"
              />
              <p className="text-xs text-zinc-400 mt-1">{form.bio.length}/5000</p>
            </div>
            <button
              data-testid="profile-save-button"
              onClick={save}
              disabled={busy}
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-blue-700 text-white text-sm font-semibold hover:bg-blue-900 disabled:opacity-50"
            >
              <Save className="w-4 h-4" /> {busy ? "Saving…" : "Save profile"}
            </button>
          </section>
        </div>
      )}
    </div>
  );
}
