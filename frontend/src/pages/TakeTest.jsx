import { useEffect, useState, useRef } from "react";
import { useParams, Link } from "react-router-dom";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Clock, ArrowLeft, Award } from "lucide-react";

function Scorecard({ attempt }) {
  const pct = attempt.total ? Math.round((attempt.score / attempt.total) * 100) : 0;
  return (
    <div className="max-w-md mx-auto border border-zinc-200 p-8 text-center" data-testid="test-scorecard">
      <Award className="w-10 h-10 text-blue-700 mx-auto" strokeWidth={1.5} />
      <h2 className="font-heading text-2xl font-black mt-4">Test Submitted</h2>
      <div className="font-heading text-5xl font-black mt-6 text-blue-700" data-testid="scorecard-score">
        {attempt.score}<span className="text-2xl text-zinc-400"> / {attempt.total}</span>
      </div>
      <p className="text-sm text-zinc-500 mt-2">
        {attempt.correct_count} of {attempt.question_count} correct · {pct}%
      </p>
      <div className="mt-8 flex justify-center gap-3 flex-wrap">
        <Link to={`/app/tests/${attempt.test_id}/review`} data-testid="review-answers-button" className="inline-block px-6 py-2.5 text-sm font-semibold border border-zinc-300 hover:bg-zinc-100 transition-colors">
          Review answers
        </Link>
        <Link to={`/app/tests/${attempt.test_id}/leaderboard`} data-testid="scorecard-leaderboard-button" className="inline-block px-6 py-2.5 text-sm font-semibold border border-zinc-300 hover:bg-zinc-100 transition-colors">
          Leaderboard
        </Link>
        <Link to="/app/tests" data-testid="back-to-tests-button" className="inline-block px-6 py-2.5 text-sm font-semibold bg-blue-700 text-white hover:bg-blue-900 transition-colors">
          Back to tests
        </Link>
      </div>
    </div>
  );
}

export default function TakeTest() {
  const { id } = useParams();
  const [test, setTest] = useState(null);
  const [answers, setAnswers] = useState({});
  const [attempt, setAttempt] = useState(null);
  const [secondsLeft, setSecondsLeft] = useState(null);
  const submittedRef = useRef(false);

  useEffect(() => {
    api.get(`/tests/${id}`).then((r) => {
      setTest(r.data);
      if (r.data.my_attempt) setAttempt(r.data.my_attempt);
      else setSecondsLeft(r.data.duration_min * 60);
    });
  }, [id]);

  useEffect(() => {
    if (secondsLeft == null || attempt) return;
    if (secondsLeft <= 0) {
      submit();
      return;
    }
    const t = setTimeout(() => setSecondsLeft((s) => s - 1), 1000);
    return () => clearTimeout(t);
  }, [secondsLeft, attempt]);

  const submit = async () => {
    if (submittedRef.current) return;
    submittedRef.current = true;
    try {
      const { data } = await api.post(`/tests/${id}/attempt`, { answers });
      setAttempt(data);
      toast.success("Test submitted");
    } catch (e) {
      submittedRef.current = false;
      toast.error(formatApiError(e));
    }
  };

  if (!test) return <p className="text-sm text-zinc-500">Loading test…</p>;
  if (attempt) return <Scorecard attempt={attempt} />;

  const mins = Math.floor((secondsLeft || 0) / 60);
  const secs = (secondsLeft || 0) % 60;

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <Link to="/app/tests" className="inline-flex items-center gap-1.5 text-sm text-zinc-500 hover:text-zinc-950">
        <ArrowLeft className="w-4 h-4" /> Exit test
      </Link>
      <div className="sticky top-14 md:top-0 z-30 bg-white border border-zinc-200 px-5 py-4 flex items-center justify-between">
        <div>
          <h1 className="font-heading font-black text-lg" data-testid="take-test-title">{test.title}</h1>
          <p className="text-xs text-zinc-500">{test.questions.length} questions · {test.total_marks} marks</p>
        </div>
        <div className={`flex items-center gap-2 font-mono font-bold text-lg ${secondsLeft < 120 ? "text-red-600" : "text-zinc-950"}`} data-testid="test-timer">
          <Clock className="w-5 h-5" />
          {String(mins).padStart(2, "0")}:{String(secs).padStart(2, "0")}
        </div>
      </div>

      {test.questions.map((q, qi) => (
        <div key={q.id} className="border border-zinc-200 p-6" data-testid={`question-${qi}`}>
          <div className="flex justify-between gap-4">
            <p className="font-semibold text-sm leading-relaxed">
              <span className="text-zinc-400 mr-2">Q{qi + 1}.</span>{q.text}
            </p>
            <span className="text-xs text-zinc-400 shrink-0">{q.marks} marks</span>
          </div>
          <div className="mt-4 space-y-2">
            {q.options.map((opt, oi) => (
              <label
                key={oi}
                data-testid={`question-${qi}-option-${oi}`}
                className={`flex items-center gap-3 border px-4 py-2.5 text-sm cursor-pointer transition-colors ${
                  answers[q.id] === oi ? "border-blue-700 bg-blue-50 font-semibold" : "border-zinc-200 hover:bg-zinc-50"
                }`}
              >
                <input
                  type="radio"
                  name={q.id}
                  checked={answers[q.id] === oi}
                  onChange={() => setAnswers({ ...answers, [q.id]: oi })}
                  className="accent-blue-700"
                />
                {opt}
              </label>
            ))}
          </div>
        </div>
      ))}

      <div className="flex items-center justify-between border-t border-zinc-200 pt-6 pb-12">
        <p className="text-sm text-zinc-500">{Object.keys(answers).length} of {test.questions.length} answered</p>
        <button onClick={submit} data-testid="submit-test-button" className="px-8 py-3 font-semibold bg-blue-700 text-white hover:bg-blue-900 transition-colors">
          Submit test
        </button>
      </div>
    </div>
  );
}
