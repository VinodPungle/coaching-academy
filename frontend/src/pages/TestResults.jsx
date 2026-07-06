import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "@/lib/api";
import { ArrowLeft } from "lucide-react";
import dayjs from "dayjs";

export default function TestResults() {
  const { id } = useParams();
  const [test, setTest] = useState(null);
  const [attempts, setAttempts] = useState([]);

  useEffect(() => {
    api.get(`/tests/${id}`).then((r) => setTest(r.data));
    api.get(`/tests/${id}/attempts`).then((r) => setAttempts(r.data));
  }, [id]);

  if (!test) return <p className="text-sm text-zinc-500">Loading…</p>;

  const avg = attempts.length ? Math.round(attempts.reduce((s, a) => s + (a.total ? (a.score / a.total) * 100 : 0), 0) / attempts.length) : 0;

  return (
    <div className="space-y-6">
      <Link to="/app/tests" className="inline-flex items-center gap-1.5 text-sm text-zinc-500 hover:text-zinc-950">
        <ArrowLeft className="w-4 h-4" /> Back to tests
      </Link>
      <div>
        <span className="text-xs uppercase tracking-[0.2em] font-semibold text-blue-700">{test.subject}</span>
        <h1 className="font-heading text-3xl font-black tracking-tight mt-1" data-testid="results-test-title">{test.title} — Results</h1>
      </div>
      <div className="grid grid-cols-3 gap-4 max-w-lg">
        {[["Attempts", attempts.length], ["Avg score", `${avg}%`], ["Total marks", test.total_marks]].map(([l, v]) => (
          <div key={l} className="border border-zinc-200 p-4">
            <div className="font-heading text-2xl font-black">{v}</div>
            <div className="text-xs uppercase tracking-[0.15em] text-zinc-500 mt-1">{l}</div>
          </div>
        ))}
      </div>
      {attempts.length === 0 ? (
        <p className="text-sm text-zinc-500" data-testid="no-attempts-message">No students have attempted this test yet.</p>
      ) : (
        <div className="border border-zinc-200 overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-zinc-50 text-left text-xs uppercase tracking-[0.1em] text-zinc-500">
              <tr>
                <th className="px-5 py-3 font-semibold">Rank</th>
                <th className="px-5 py-3 font-semibold">Student</th>
                <th className="px-5 py-3 font-semibold">Score</th>
                <th className="px-5 py-3 font-semibold">Correct</th>
                <th className="px-5 py-3 font-semibold">Submitted</th>
              </tr>
            </thead>
            <tbody>
              {attempts.map((a, i) => (
                <tr key={a.id} className="border-t border-zinc-100" data-testid={`attempt-row-${a.id}`}>
                  <td className="px-5 py-3 font-bold">#{i + 1}</td>
                  <td className="px-5 py-3 font-medium">{a.student_name}</td>
                  <td className="px-5 py-3 font-semibold text-blue-700">{a.score} / {a.total}</td>
                  <td className="px-5 py-3 text-zinc-500">{a.correct_count} / {a.question_count}</td>
                  <td className="px-5 py-3 text-zinc-500">{dayjs(a.submitted_at).format("D MMM, h:mm A")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
