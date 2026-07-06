import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api, formatApiError } from "@/lib/api";
import { ArrowLeft, CheckCircle2, XCircle, MinusCircle } from "lucide-react";

export default function TestReview() {
  const { id } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get(`/tests/${id}/review`)
      .then((r) => setData(r.data))
      .catch((e) => setError(formatApiError(e)));
  }, [id]);

  if (error)
    return (
      <div className="space-y-4">
        <p className="text-sm text-red-600 border border-red-200 bg-red-50 px-4 py-3" data-testid="review-error">{error}</p>
        <Link to="/app/tests" className="text-sm font-semibold text-blue-700 hover:underline">← Back to tests</Link>
      </div>
    );
  if (!data) return <p className="text-sm text-zinc-500">Loading review…</p>;

  const { test, attempt } = data;
  const pct = attempt.total ? Math.round((attempt.score / attempt.total) * 100) : 0;

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <Link to="/app/tests" className="inline-flex items-center gap-1.5 text-sm text-zinc-500 hover:text-zinc-950" data-testid="review-back-link">
        <ArrowLeft className="w-4 h-4" /> Back to tests
      </Link>
      <div>
        <span className="text-xs uppercase tracking-[0.2em] font-semibold text-blue-700">{test.subject} · Answer Review</span>
        <h1 className="font-heading text-3xl font-black tracking-tight mt-1" data-testid="review-test-title">{test.title}</h1>
      </div>
      <div className="grid grid-cols-3 gap-4 max-w-lg">
        {[["Your score", `${attempt.score} / ${attempt.total}`], ["Correct", `${attempt.correct_count} / ${attempt.question_count}`], ["Percentage", `${pct}%`]].map(([l, v]) => (
          <div key={l} className="border border-zinc-200 p-4">
            <div className="font-heading text-xl font-black" data-testid={`review-stat-${l.toLowerCase().replace(" ", "-")}`}>{v}</div>
            <div className="text-xs uppercase tracking-[0.15em] text-zinc-500 mt-1">{l}</div>
          </div>
        ))}
      </div>

      <div className="space-y-4 pb-12">
        {test.questions.map((q, qi) => {
          const chosen = attempt.answers?.[q.id];
          const isCorrect = chosen === q.correct_index;
          const skipped = chosen === undefined || chosen === null;
          return (
            <div key={q.id} className="border border-zinc-200 p-6" data-testid={`review-question-${qi}`}>
              <div className="flex items-start justify-between gap-4">
                <p className="font-semibold text-sm leading-relaxed">
                  <span className="text-zinc-400 mr-2">Q{qi + 1}.</span>{q.text}
                </p>
                <span className={`shrink-0 inline-flex items-center gap-1 text-xs font-bold px-2 py-1 ${isCorrect ? "bg-green-50 text-green-700" : skipped ? "bg-zinc-100 text-zinc-500" : "bg-red-50 text-red-600"}`} data-testid={`review-verdict-${qi}`}>
                  {isCorrect ? <CheckCircle2 className="w-3.5 h-3.5" /> : skipped ? <MinusCircle className="w-3.5 h-3.5" /> : <XCircle className="w-3.5 h-3.5" />}
                  {isCorrect ? `+${q.marks}` : skipped ? "Skipped" : "0"}
                </span>
              </div>
              <div className="mt-4 space-y-2">
                {q.options.map((opt, oi) => {
                  const isAnswer = oi === q.correct_index;
                  const isChosen = oi === chosen;
                  let cls = "border-zinc-200 text-zinc-600";
                  if (isAnswer) cls = "border-green-600 bg-green-50 text-green-800 font-semibold";
                  else if (isChosen) cls = "border-red-400 bg-red-50 text-red-700";
                  return (
                    <div key={oi} className={`flex items-center justify-between gap-3 border px-4 py-2.5 text-sm ${cls}`}>
                      <span><span className="text-zinc-400 mr-2">{String.fromCharCode(65 + oi)}.</span>{opt}</span>
                      <span className="text-[10px] uppercase tracking-[0.15em] font-bold shrink-0">
                        {isAnswer ? "Correct answer" : isChosen ? "Your answer" : ""}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
