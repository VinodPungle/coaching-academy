// "My Profile" self-service editor for a teacher ("/app/my-profile") —
// edits the display name/subtitle/bio/photo shown on the public
// TeachersPublic.jsx directory. Route-guards itself against non-teacher
// roles rather than relying on App.js to hide the route.
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Save } from "lucide-react";
import { api, formatApiError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import ProfilePhotoEditor from "@/components/ProfilePhotoEditor";

export default function TeacherProfileEdit() {
  const { user } = useAuth();
  const [form, setForm] = useState({ display_name: "", subtitle: "", bio: "", photo_url: "" });
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (user?.role !== "teacher") { setLoading(false); return; }
    api.get("/teacher-profiles/me")
      .then(({ data }) => setForm({
        display_name: data.display_name || data.name || "",
        subtitle: data.subtitle || "",
        bio: data.bio || "",
        photo_url: data.photo_url || "",
      }))
      .catch((err) => toast.error(formatApiError(err)))
      .finally(() => setLoading(false));
  }, [user]);

  if (user?.role !== "teacher") {
    return <p className="text-sm text-red-600" data-testid="my-profile-forbidden">This page is for teachers only.</p>;
  }

  const save = async () => {
    setBusy(true);
    try {
      await api.put(`/teacher-profiles/${user.id}`, form);
      toast.success("Profile updated");
    } catch (err) { toast.error(formatApiError(err)); }
    finally { setBusy(false); }
  };

  if (loading) return <p className="text-sm text-zinc-500">Loading…</p>;

  return (
    <div className="space-y-6" data-testid="teacher-profile-edit">
      <div>
        <h1 className="font-heading text-2xl sm:text-3xl font-black tracking-tight">My public profile</h1>
        <p className="text-sm text-zinc-500 mt-1">This is what students see on the public Teachers page.</p>
      </div>

      <section className="border border-zinc-200 p-5 md:p-6 space-y-4 max-w-2xl">
        <div>
          <label className="text-xs uppercase tracking-[0.15em] font-semibold text-zinc-500">Profile photo</label>
          <div className="mt-2">
            <ProfilePhotoEditor value={form.photo_url} onChange={(v) => setForm({ ...form, photo_url: v })} testidPrefix="my-profile-photo" />
          </div>
        </div>
        <div>
          <label className="text-xs uppercase tracking-[0.15em] font-semibold text-zinc-500">Display name</label>
          <input
            data-testid="my-profile-display-name"
            value={form.display_name}
            maxLength={200}
            onChange={(e) => setForm({ ...form, display_name: e.target.value })}
            className="mt-1.5 w-full border border-zinc-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-700"
          />
        </div>
        <div>
          <label className="text-xs uppercase tracking-[0.15em] font-semibold text-zinc-500">Subtitle</label>
          <input
            data-testid="my-profile-subtitle"
            value={form.subtitle}
            maxLength={300}
            onChange={(e) => setForm({ ...form, subtitle: e.target.value })}
            className="mt-1.5 w-full border border-zinc-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-700"
          />
        </div>
        <div>
          <label className="text-xs uppercase tracking-[0.15em] font-semibold text-zinc-500">Bio</label>
          <textarea
            data-testid="my-profile-bio"
            value={form.bio}
            maxLength={5000}
            rows={14}
            onChange={(e) => setForm({ ...form, bio: e.target.value })}
            className="mt-1.5 w-full border border-zinc-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-700 resize-none"
          />
          <p className="text-xs text-zinc-400 mt-1">{form.bio.length}/5000</p>
        </div>
        <button
          data-testid="my-profile-save"
          onClick={save}
          disabled={busy}
          className="inline-flex items-center gap-2 px-5 py-2.5 bg-blue-700 text-white text-sm font-semibold hover:bg-blue-900 disabled:opacity-50"
        >
          <Save className="w-4 h-4" /> {busy ? "Saving…" : "Save profile"}
        </button>
      </section>
    </div>
  );
}
