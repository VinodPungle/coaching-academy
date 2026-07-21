// Public teacher directory ("/teachers") — no login required. Lists every
// teacher's public profile (GET /teacher-profiles); the demo teacher
// account is excluded server-side. Teachers edit their own bio/photo via
// TeacherProfileEdit.jsx; admins can edit any via AdminTeacherProfiles.jsx.
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { GraduationCap, ArrowLeft, User } from "lucide-react";
import { api, fileUrl } from "@/lib/api";
import { useSiteConfig } from "@/context/SiteConfigContext";

const resolvePhoto = (u) => {
  if (!u) return "";
  return u.startsWith("/api/files/") ? fileUrl(u) : u;
};

export default function TeachersPublic() {
  const { brand_name, landing } = useSiteConfig();
  const [teachers, setTeachers] = useState([]);
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/teacher-profiles")
      .then(({ data }) => {
        setTeachers(data || []);
        if (data && data.length) setSelected(data[0]);
      })
      .catch(() => setTeachers([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="min-h-screen bg-white text-zinc-950">
      <header className="sticky top-0 z-40 bg-white/80 backdrop-blur-xl border-b border-zinc-200/50">
        <div className="max-w-6xl mx-auto flex items-center justify-between px-4 md:px-8 h-16">
          <Link to="/" className="flex items-center gap-2 min-w-0">
            <GraduationCap className="w-7 h-7 text-blue-700 shrink-0" />
            <span className="font-heading font-black tracking-tight text-sm sm:text-base md:text-lg leading-tight truncate">{brand_name}</span>
          </Link>
          <Link to="/" data-testid="teachers-back-link" className="text-sm font-semibold text-zinc-600 hover:text-zinc-950 inline-flex items-center gap-1">
            <ArrowLeft className="w-4 h-4" /> Home
          </Link>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-4 md:px-8 py-10 md:py-14">
        <p className="text-xs uppercase tracking-[0.2em] font-semibold text-blue-700 mb-3">{landing.teachers_menu_label}</p>
        <h1 className="font-heading text-3xl sm:text-4xl lg:text-5xl tracking-tighter font-black leading-[1.05]" data-testid="teachers-heading">
          Meet our faculty
        </h1>

        {loading ? (
          <p className="mt-10 text-sm text-zinc-500" data-testid="teachers-loading">Loading…</p>
        ) : teachers.length === 0 ? (
          <p className="mt-10 text-sm text-zinc-500" data-testid="teachers-empty">No teacher profiles yet.</p>
        ) : (
          <div className="mt-10 grid md:grid-cols-[240px_1fr] gap-6 md:gap-10">
            <aside className="border border-zinc-200 divide-y divide-zinc-200 self-start" data-testid="teachers-list">
              {teachers.map((t) => (
                <button
                  key={t.id}
                  onClick={() => setSelected(t)}
                  data-testid={`teacher-item-${t.id}`}
                  className={`w-full text-left px-4 py-3.5 flex items-center gap-3 transition-colors ${selected?.id === t.id ? "bg-blue-700 text-white" : "hover:bg-zinc-50"}`}
                >
                  <div className={`w-9 h-9 flex items-center justify-center rounded-full ${selected?.id === t.id ? "bg-white/20" : "bg-zinc-100"}`}>
                    <User className={`w-4 h-4 ${selected?.id === t.id ? "text-white" : "text-zinc-500"}`} />
                  </div>
                  <div className="min-w-0">
                    <div className="text-sm font-semibold truncate">{t.display_name || t.name}</div>
                    {t.subtitle && <div className={`text-xs truncate ${selected?.id === t.id ? "text-white/80" : "text-zinc-500"}`}>{t.subtitle}</div>}
                  </div>
                </button>
              ))}
            </aside>
            <article className="border border-zinc-200 p-6 md:p-8" data-testid="teacher-profile">
              {selected ? (
                <div className="grid md:grid-cols-[1fr_180px] gap-6 md:gap-8">
                  <div className="min-w-0 order-2 md:order-1">
                    <h2 className="font-heading text-2xl md:text-3xl font-black tracking-tight" data-testid="teacher-name">{selected.display_name || selected.name}</h2>
                    {selected.subtitle && <p className="text-sm text-zinc-500 mt-1" data-testid="teacher-subtitle">{selected.subtitle}</p>}
                    {selected.bio ? (
                      <p className="mt-5 text-[15px] leading-relaxed text-zinc-700 whitespace-pre-line" data-testid="teacher-bio">
                        {selected.bio}
                      </p>
                    ) : (
                      <p className="mt-5 text-sm text-zinc-400 italic" data-testid="teacher-bio-empty">Profile bio not added yet.</p>
                    )}
                  </div>
                  <div className="order-1 md:order-2 shrink-0">
                    <div className="w-[145px] h-[180px] md:w-[160px] md:h-[200px] bg-zinc-100 border border-zinc-200 overflow-hidden flex items-center justify-center" data-testid="teacher-photo-wrap">
                      {selected.photo_url ? (
                        <img
                          src={resolvePhoto(selected.photo_url)}
                          alt={selected.display_name || selected.name}
                          className="w-full h-full object-cover"
                          data-testid="teacher-photo-img"
                          onError={(e) => { e.currentTarget.style.display = 'none'; }}
                        />
                      ) : (
                        <User className="w-16 h-16 text-zinc-400" strokeWidth={1.5} data-testid="teacher-photo-placeholder" />
                      )}
                    </div>
                  </div>
                </div>
              ) : (
                <p className="text-sm text-zinc-500">Select a teacher to view their profile.</p>
              )}
            </article>
          </div>
        )}
      </div>
    </div>
  );
}
