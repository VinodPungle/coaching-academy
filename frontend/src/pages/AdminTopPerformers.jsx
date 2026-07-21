// Admin-only leaderboard ("/app/top-performers") — top students ranked by
// average test score %, grouped either by course or by batch (toggle
// below). Backed by a single GET /admin/top-performers call that computes
// both groupings server-side.
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Trophy, BookOpen, Users } from "lucide-react";

export default function AdminTopPerformers() {
  const [data, setData] = useState(null);
  const [tab, setTab] = useState("course");

  useEffect(() => {
    api.get("/admin/top-performers?limit=5").then((r) => setData(r.data));
  }, []);

  if (!data) return <p className="text-sm text-zinc-500" data-testid="top-performers-loading">Loading top performers…</p>;

  const groups = tab === "course" ? data.per_course : data.per_batch;

  return (
    <div className="space-y-6" data-testid="admin-top-performers-page">
      <div>
        <p className="text-xs uppercase tracking-[0.2em] font-semibold text-red-600">Admin Panel</p>
        <h1 className="font-heading text-3xl font-black tracking-tight mt-1">Top Performers</h1>
        <p className="text-sm text-zinc-500 mt-2">Ranked by average test score (%). Only students with at least one test attempt are included.</p>
      </div>

      <div className="flex gap-px bg-zinc-200 border border-zinc-200 w-fit">
        {[["course", "By Course", BookOpen], ["batch", "By Batch", Users]].map(([k, label, Icon]) => (
          <button
            key={k}
            data-testid={`top-performers-tab-${k}`}
            onClick={() => setTab(k)}
            className={`inline-flex items-center gap-2 px-5 py-2 text-sm font-semibold transition-colors ${tab === k ? "bg-blue-700 text-white" : "bg-white text-zinc-500 hover:bg-zinc-50"}`}
          >
            <Icon className="w-4 h-4" />
            {label}
          </button>
        ))}
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        {groups.length === 0 && <p className="text-sm text-zinc-500" data-testid="top-performers-empty">No data yet.</p>}
        {groups.map((g) => {
          const key = tab === "course" ? g.course_id : g.batch_id;
          const heading = tab === "course" ? g.course_title : g.batch_name;
          const subtitle = tab === "course" ? "" : g.course_title;
          return (
            <div key={key} className="border border-zinc-200" data-testid={`top-performers-group-${key}`}>
              <div className="px-5 py-4 border-b border-zinc-200 bg-zinc-50">
                <h2 className="font-heading font-bold">{heading}</h2>
                {subtitle && <p className="text-xs text-zinc-500 mt-0.5">{subtitle}</p>}
              </div>
              {g.top.length === 0 ? (
                <p className="px-5 py-4 text-xs text-zinc-400">No attempts yet.</p>
              ) : (
                <ol className="divide-y divide-zinc-100">
                  {g.top.map((r, i) => (
                    <li key={r.student_id} className="px-5 py-3 flex items-center gap-3" data-testid={`top-performer-${key}-${i}`}>
                      <div className={`shrink-0 w-8 h-8 flex items-center justify-center text-xs font-bold ${i === 0 ? "bg-yellow-400" : i === 1 ? "bg-zinc-300" : i === 2 ? "bg-amber-600 text-white" : "bg-zinc-100"}`}>
                        {i === 0 ? <Trophy className="w-4 h-4" /> : i + 1}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="font-semibold text-sm">{r.student_name}</div>
                        <div className="text-xs text-zinc-500">{r.attempts} test{r.attempts !== 1 ? "s" : ""} attempted</div>
                      </div>
                      <div className="text-right shrink-0">
                        <div className="font-heading text-xl font-black">{r.avg_pct}%</div>
                        <div className="text-[10px] uppercase tracking-[0.15em] text-zinc-400">avg score</div>
                      </div>
                    </li>
                  ))}
                </ol>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
