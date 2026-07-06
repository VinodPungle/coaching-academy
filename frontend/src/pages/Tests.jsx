import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { FileQuestion, Plus, Trash2, Clock } from "lucide-react";

export default function TestsPage() {
  const { user } = useAuth();
  const [tests, setTests] = useState([]);
  const isTeacher = user.role !== "student";

  const load = () => api.get("/tests").then((r) => setTests(r.data));
  useEffect(() => { load(); }, []);

  const remove = async (id) => {
    await api.delete(`/tests/${id}`);
    toast.success("Test deleted");
    load();
  };

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between flex-wrap gap-4">
        <h1 className="font-heading text-3xl font-black tracking-tight">Mock Tests</h1>
        {isTeacher && (
          <Link to="/app/tests/new" data-testid="create-test-button" className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-semibold bg-blue-700 text-white hover:bg-blue-900 transition-colors">
            <Plus className="w-4 h-4" /> Create test
          </Link>
        )}
      </div>

      <div className="grid sm:grid-cols-2 gap-4">
        {tests.map((t) => (
          <div key={t.id} className="border border-zinc-200 p-6 hover:border-zinc-300 hover:shadow-sm transition-all" data-testid={`test-card-${t.id}`}>
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-xs uppercase tracking-[0.15em] font-semibold text-blue-700">{t.subject}</span>
                  {t.course_name && <span className="text-[10px] uppercase tracking-[0.1em] font-bold bg-zinc-950 text-white px-1.5 py-0.5" data-testid={`test-course-badge-${t.id}`}>{t.course_name}</span>}
                </div>
                <h3 className="font-heading font-bold mt-1">{t.title}</h3>
              </div>
              <FileQuestion className="w-5 h-5 text-zinc-300 shrink-0" />
            </div>
            <div className="flex items-center gap-4 text-xs text-zinc-500 mt-3">
              <span>{t.questions?.length ?? 0} questions</span>
              <span className="inline-flex items-center gap-1"><Clock className="w-3.5 h-3.5" />{t.duration_min} min</span>
              <span>{t.total_marks} marks</span>
            </div>
            <div className="mt-5">
              {isTeacher ? (
                <div className="flex items-center justify-between">
                  <Link to={`/app/tests/${t.id}/results`} data-testid={`view-results-${t.id}`} className="text-sm font-semibold text-blue-700 hover:underline">
                    {t.attempt_count} attempts — View results →
                  </Link>
                  <button onClick={() => remove(t.id)} data-testid={`delete-test-${t.id}`} className="p-2 border border-zinc-300 text-zinc-500 hover:text-red-600 hover:border-red-300 transition-colors">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ) : t.my_attempt ? (
                <div className="space-y-2">
                  <div className="flex items-center justify-between border border-green-200 bg-green-50 px-4 py-2.5">
                    <span className="text-sm font-semibold text-green-700">Attempted</span>
                    <span className="text-sm font-bold text-green-700" data-testid={`test-score-${t.id}`}>{t.my_attempt.score} / {t.my_attempt.total}</span>
                  </div>
                  <Link to={`/app/tests/${t.id}/review`} data-testid={`review-test-${t.id}`} className="block text-center py-2 text-sm font-semibold border border-zinc-300 hover:bg-zinc-100 transition-colors">
                    Review answers
                  </Link>
                </div>
              ) : (
                <Link to={`/app/tests/${t.id}/take`} data-testid={`start-test-${t.id}`} className="block text-center py-2.5 text-sm font-semibold bg-blue-700 text-white hover:bg-blue-900 transition-colors">
                  Start test
                </Link>
              )}
            </div>
          </div>
        ))}
      </div>
      {tests.length === 0 && <p className="text-sm text-zinc-500 py-8" data-testid="tests-empty-state">{isTeacher ? "You haven't created any tests yet." : "No tests published yet."}</p>}
    </div>
  );
}
