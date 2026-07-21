// Teacher-only test author/editor ("/app/tests/new" and
// "/app/tests/:id/edit" — same component for both, branching on whether
// an :id param is present). Every question is fixed at 4 options; on save
// the whole question list is sent as a full replace (see courses' sibling
// pattern — the backend re-generates every question id on every edit, so
// nothing here should assume a question's id survives an edit).
import { useState, useEffect } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Plus, Trash2, ArrowLeft } from "lucide-react";

const emptyQ = () => ({ text: "", options: ["", "", "", ""], correct_index: 0, marks: 4 });

export default function TestBuilder() {
  const navigate = useNavigate();
  const { id: editId } = useParams();
  const isEdit = Boolean(editId);
  const [meta, setMeta] = useState({ title: "", subject: "Physics", duration_min: 30, course_id: "", retakes_allowed: false });
  const [questions, setQuestions] = useState([emptyQ()]);
  const [teacherCourses, setTeacherCourses] = useState([]);
  const [loading, setLoading] = useState(isEdit);

  useEffect(() => {
    api.get("/teacher/courses").then((r) => setTeacherCourses(r.data));
    if (isEdit) {
      api.get(`/tests/${editId}`).then((r) => {
        const t = r.data;
        setMeta({
          title: t.title || "",
          subject: t.subject || "Physics",
          duration_min: t.duration_min || 30,
          course_id: t.course_id || "",
          retakes_allowed: t.retakes_allowed || false,
        });
        const loaded = (t.questions || []).map((q) => ({
          text: q.text,
          options: (q.options && q.options.length === 4) ? q.options : ["", "", "", ""],
          correct_index: q.correct_index ?? 0,
          marks: q.marks ?? 4,
        }));
        setQuestions(loaded.length ? loaded : [emptyQ()]);
        setLoading(false);
      }).catch((err) => {
        toast.error(formatApiError(err));
        navigate("/app/tests");
      });
    }
  }, [editId, isEdit, navigate]);

  const setQ = (i, patch) => setQuestions(questions.map((q, idx) => (idx === i ? { ...q, ...patch } : q)));
  const setOpt = (i, oi, v) => setQ(i, { options: questions[i].options.map((o, idx) => (idx === oi ? v : o)) });

  const submit = async (e) => {
    e.preventDefault();
    const valid = questions.filter((q) => q.text.trim() && q.options.every((o) => o.trim()));
    if (valid.length === 0) {
      toast.error("Add at least one complete question (all 4 options filled)");
      return;
    }
    const payload = {
      ...meta,
      course_id: meta.course_id || null,
      duration_min: Number(meta.duration_min),
      published: true,
      retakes_allowed: Boolean(meta.retakes_allowed),
      questions: valid.map((q) => ({ ...q, marks: Number(q.marks), correct_index: Number(q.correct_index) })),
    };
    try {
      if (isEdit) {
        await api.put(`/tests/${editId}`, payload);
        toast.success("Test updated");
      } else {
        await api.post("/tests", payload);
        toast.success("Test published");
      }
      navigate("/app/tests");
    } catch (err) {
      toast.error(formatApiError(err));
    }
  };

  if (loading) return <p className="text-sm text-zinc-500" data-testid="test-builder-loading">Loading test…</p>;

  return (
    <form onSubmit={submit} className="max-w-3xl mx-auto space-y-6">
      <Link to="/app/tests" className="inline-flex items-center gap-1.5 text-sm text-zinc-500 hover:text-zinc-950">
        <ArrowLeft className="w-4 h-4" /> Back to tests
      </Link>
      <h1 className="font-heading text-3xl font-black tracking-tight" data-testid="test-builder-heading">
        {isEdit ? "Modify Test" : "Create Mock Test"}
      </h1>

      <div className="border border-zinc-200 p-6 grid sm:grid-cols-3 gap-4">
        <div className="sm:col-span-3">
          <label className="text-xs uppercase tracking-[0.15em] font-semibold text-zinc-500">Test title</label>
          <input data-testid="test-title-input" required value={meta.title} onChange={(e) => setMeta({ ...meta, title: e.target.value })} placeholder="Physics Mock Test 2" className="mt-1 w-full border border-zinc-300 px-3 py-2 text-sm" />
        </div>
        <div>
          <label className="text-xs uppercase tracking-[0.15em] font-semibold text-zinc-500">Subject</label>
          <select data-testid="test-subject-select" value={meta.subject} onChange={(e) => setMeta({ ...meta, subject: e.target.value })} className="mt-1 w-full border border-zinc-300 px-3 py-2 text-sm bg-white">
            {["Physics", "Chemistry", "Mathematics", "Biotechnology"].map((s) => <option key={s}>{s}</option>)}
          </select>
        </div>
        <div>
          <label className="text-xs uppercase tracking-[0.15em] font-semibold text-zinc-500">Duration (min)</label>
          <input data-testid="test-duration-input" type="number" min="1" value={meta.duration_min} onChange={(e) => setMeta({ ...meta, duration_min: e.target.value })} className="mt-1 w-full border border-zinc-300 px-3 py-2 text-sm" />
        </div>
        <div>
          <label className="text-xs uppercase tracking-[0.15em] font-semibold text-zinc-500">Course (optional)</label>
          <select data-testid="test-course-select" value={meta.course_id} onChange={(e) => setMeta({ ...meta, course_id: e.target.value })} className="mt-1 w-full border border-zinc-300 px-3 py-2 text-sm bg-white">
            <option value="">All students</option>
            {teacherCourses.map((c) => <option key={c.id} value={c.id}>{c.title}</option>)}
          </select>
        </div>
        <div className="sm:col-span-3">
          <label className="flex items-center gap-2 text-sm cursor-pointer">
            <input
              type="checkbox"
              checked={meta.retakes_allowed}
              onChange={(e) => setMeta({ ...meta, retakes_allowed: e.target.checked })}
              data-testid="test-retakes-checkbox"
              className="accent-blue-700 w-4 h-4"
            />
            <span className="font-semibold">Allow retakes</span>
            <span className="text-xs text-zinc-500">— students can reattempt this test; their latest score is kept.</span>
          </label>
        </div>
      </div>

      {questions.map((q, i) => (
        <div key={i} className="border border-zinc-200 p-6 space-y-4" data-testid={`builder-question-${i}`}>
          <div className="flex items-center justify-between">
            <h3 className="font-heading font-bold">Question {i + 1}</h3>
            {questions.length > 1 && (
              <button type="button" onClick={() => setQuestions(questions.filter((_, idx) => idx !== i))} className="p-1.5 text-zinc-400 hover:text-red-600">
                <Trash2 className="w-4 h-4" />
              </button>
            )}
          </div>
          <textarea data-testid={`question-text-input-${i}`} required value={q.text} onChange={(e) => setQ(i, { text: e.target.value })} placeholder="Enter the question…" rows={2} className="w-full border border-zinc-300 px-3 py-2 text-sm" />
          <div className="grid sm:grid-cols-2 gap-3">
            {q.options.map((opt, oi) => (
              <div key={oi} className="flex items-center gap-2">
                <input
                  type="radio"
                  name={`correct-${i}`}
                  checked={Number(q.correct_index) === oi}
                  onChange={() => setQ(i, { correct_index: oi })}
                  data-testid={`correct-option-${i}-${oi}`}
                  className="accent-blue-700 shrink-0"
                  title="Mark as correct answer"
                />
                <input data-testid={`option-input-${i}-${oi}`} required value={opt} onChange={(e) => setOpt(i, oi, e.target.value)} placeholder={`Option ${String.fromCharCode(65 + oi)}`} className="flex-1 border border-zinc-300 px-3 py-2 text-sm" />
              </div>
            ))}
          </div>
          <div className="flex items-center gap-2">
            <label className="text-xs uppercase tracking-[0.15em] font-semibold text-zinc-500">Marks</label>
            <input type="number" min="1" value={q.marks} onChange={(e) => setQ(i, { marks: e.target.value })} className="w-20 border border-zinc-300 px-2 py-1 text-sm" />
            <span className="text-xs text-zinc-400 ml-2">Radio button marks the correct option</span>
          </div>
        </div>
      ))}

      <div className="flex items-center justify-between pb-12">
        <button type="button" onClick={() => setQuestions([...questions, emptyQ()])} data-testid="add-question-button" className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-semibold border border-zinc-300 hover:bg-zinc-100 transition-colors">
          <Plus className="w-4 h-4" /> Add question
        </button>
        <button data-testid="publish-test-button" className="px-8 py-3 font-semibold bg-blue-700 text-white hover:bg-blue-900 transition-colors">
          {isEdit ? "Save changes" : "Publish test"}
        </button>
      </div>
    </form>
  );
}
