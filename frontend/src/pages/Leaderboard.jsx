// Per-test ranked leaderboard ("/app/tests/:id/leaderboard"), open to any
// authenticated user — the backend also computes the caller's own
// rank/percentile if they're on the board (see test_leaderboard in
// backend/routers/tests.py).
import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "@/lib/api";
import { ArrowLeft, Trophy, Medal } from "lucide-react";
import dayjs from "dayjs";

// Gold/silver/bronze text colors for ranks 1-3.
const PODIUM = ["text-yellow-500", "text-zinc-400", "text-amber-700"];

export default function Leaderboard() {
  const { id } = useParams();
  const [data, setData] = useState(null);

  useEffect(() => {
    api.get(`/tests/${id}/leaderboard`).then((r) => setData(r.data));
  }, [id]);

  if (!data) return <p className="text-sm text-zinc-500">Loading leaderboard…</p>;

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <Link to="/app/tests" className="inline-flex items-center gap-1.5 text-sm text-zinc-500 hover:text-zinc-950" data-testid="leaderboard-back-link">
        <ArrowLeft className="w-4 h-4" /> Back to tests
      </Link>
      <div>
        <span className="text-xs uppercase tracking-[0.2em] font-semibold text-blue-700">{data.subject} · Leaderboard</span>
        <h1 className="font-heading text-3xl font-black tracking-tight mt-1" data-testid="leaderboard-title">{data.test_title}</h1>
      </div>

      {data.my_rank && (
        <div className="grid grid-cols-3 gap-4 max-w-lg">
          {[["Your rank", `#${data.my_rank}`], ["Percentile", `${data.my_percentile}`], ["Total attempts", data.attempt_count]].map(([l, v]) => (
            <div key={l} className="border border-zinc-200 p-4">
              <div className="font-heading text-2xl font-black text-blue-700" data-testid={`leaderboard-stat-${l.toLowerCase().replace(/ /g, "-")}`}>{v}</div>
              <div className="text-xs uppercase tracking-[0.15em] text-zinc-500 mt-1">{l}</div>
            </div>
          ))}
        </div>
      )}

      {data.entries.length === 0 ? (
        <p className="text-sm text-zinc-500 py-8" data-testid="leaderboard-empty">No one has attempted this test yet. Be the first!</p>
      ) : (
        <>
          <div className="grid grid-cols-3 gap-4">
            {data.entries.slice(0, 3).map((e, i) => (
              <div key={e.rank} className={`border p-5 text-center ${e.is_me ? "border-blue-700 bg-blue-50" : "border-zinc-200"}`} data-testid={`podium-${i + 1}`}>
                <Trophy className={`w-6 h-6 mx-auto ${PODIUM[i]}`} strokeWidth={1.5} />
                <div className="font-heading font-black text-lg mt-2 truncate">{e.student_name}{e.is_me ? " (You)" : ""}</div>
                <div className="text-sm font-bold text-blue-700 mt-1">{e.score} / {e.total}</div>
                <div className="text-[10px] uppercase tracking-[0.2em] text-zinc-400 mt-1">Rank #{e.rank}</div>
              </div>
            ))}
          </div>

          <div className="border border-zinc-200 overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-zinc-50 text-left text-xs uppercase tracking-[0.1em] text-zinc-500">
                <tr>
                  <th className="px-5 py-3 font-semibold">Rank</th>
                  <th className="px-5 py-3 font-semibold">Student</th>
                  <th className="px-5 py-3 font-semibold">Score</th>
                  <th className="px-5 py-3 font-semibold">Submitted</th>
                </tr>
              </thead>
              <tbody>
                {data.entries.map((e) => (
                  <tr key={e.rank} className={`border-t border-zinc-100 ${e.is_me ? "bg-blue-50 font-semibold" : ""}`} data-testid={`leaderboard-row-${e.rank}`}>
                    <td className="px-5 py-3 font-bold">
                      {e.rank <= 3 ? <Medal className={`w-4 h-4 inline mr-1 ${PODIUM[e.rank - 1]}`} /> : null}#{e.rank}
                    </td>
                    <td className="px-5 py-3">{e.student_name}{e.is_me ? " (You)" : ""}</td>
                    <td className="px-5 py-3 text-blue-700 font-semibold">{e.score} / {e.total}</td>
                    <td className="px-5 py-3 text-zinc-500">{dayjs(e.submitted_at).format("D MMM, h:mm A")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
