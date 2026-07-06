import { useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Plus, ClipboardList, Trash2 } from "lucide-react";
import dayjs from "dayjs";

export default function AssignmentsPage() {
  const { user } = useAuth();
  const [assignments, setAssignments] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ title: "", subject: "Physics", description: "", due_date: "", max_marks: 10 });
  const [submitFor, setSubmitFor] = useState(null);
  const [subForm, setSubForm] = useState({ content: "", link: "" });
  const [viewSubsFor, setViewSubsFor] = useState(null);
  const [submissions, setSubmissions] = useState([]);
  const [grades, setGrades] = useState({});

  const isTeacher = user.role !== "student";
  const load = () => api.get("/assignments").then((r) => setAssignments(r.data));
  useEffect(() => { load(); }, []);

  const create = async (e) => {
    e.preventDefault();
    try {
      await api.post("/assignments", { ...form, max_marks: Number(form.max_marks) });
      toast.success("Assignment created");
      setShowForm(false);
      setForm({ title: "", subject: "Physics", description: "", due_date: "", max_marks: 10 });
      load();
    } catch (err) {
      toast.error(formatApiError(err));
    }
  };

  const remove = async (id) => {
    await api.delete(`/assignments/${id}`);
    toast.success("Assignment deleted");
    load();
  };

  const submitWork = async (e) => {
    e.preventDefault();
    try {
      await api.post(`/assignments/${submitFor}/submit`, subForm);
      toast.success("Assignment submitted");
      setSubmitFor(null);
      setSubForm({ content: "", link: "" });
      load();
    } catch (err) {
      toast.error(formatApiError(err));
    }
  };

  const openSubmissions = async (id) => {
    setViewSubsFor(id);
    const { data } = await api.get(`/assignments/${id}/submissions`);
    setSubmissions(data);
  };

  const grade = async (subId) => {
    const g = grades[subId];
    if (!g?.grade && g?.grade !== 0) return;
    await api.put(`/submissions/${subId}/grade`, { grade: Number(g.grade), feedback: g.feedback || "" });
    toast.success("Graded");
    openSubmissions(viewSubsFor);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between flex-wrap gap-4">
        <h1 className="font-heading text-3xl font-black tracking-tight">Assignments</h1>
        {isTeacher && (
          <button onClick={() => setShowForm(!showForm)} data-testid="new-assignment-button" className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-semibold bg-blue-700 text-white hover:bg-blue-900 transition-colors">
            <Plus className="w-4 h-4" /> New assignment
          </button>
        )}
      </div>

      {isTeacher && showForm && (
        <form onSubmit={create} className="border border-zinc-200 p-6 grid sm:grid-cols-3 gap-4" data-testid="new-assignment-form">
          <div className="sm:col-span-3">
            <label className="text-xs uppercase tracking-[0.15em] font-semibold text-zinc-500">Title</label>
            <input data-testid="assignment-title-input" required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} className="mt-1 w-full border border-zinc-300 px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="text-xs uppercase tracking-[0.15em] font-semibold text-zinc-500">Subject</label>
            <select value={form.subject} onChange={(e) => setForm({ ...form, subject: e.target.value })} className="mt-1 w-full border border-zinc-300 px-3 py-2 text-sm bg-white">
              {["Physics", "Chemistry", "Mathematics", "Biotechnology", "Economics", "Geology"].map((s) => <option key={s}>{s}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs uppercase tracking-[0.15em] font-semibold text-zinc-500">Due date</label>
            <input data-testid="assignment-due-input" type="date" value={form.due_date} onChange={(e) => setForm({ ...form, due_date: e.target.value })} className="mt-1 w-full border border-zinc-300 px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="text-xs uppercase tracking-[0.15em] font-semibold text-zinc-500">Max marks</label>
            <input type="number" value={form.max_marks} onChange={(e) => setForm({ ...form, max_marks: e.target.value })} className="mt-1 w-full border border-zinc-300 px-3 py-2 text-sm" />
          </div>
          <div className="sm:col-span-3">
            <label className="text-xs uppercase tracking-[0.15em] font-semibold text-zinc-500">Instructions</label>
            <textarea data-testid="assignment-description-input" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} rows={3} className="mt-1 w-full border border-zinc-300 px-3 py-2 text-sm" />
          </div>
          <div className="sm:col-span-3 flex gap-2">
            <button data-testid="assignment-submit-button" className="px-5 py-2 text-sm font-semibold bg-blue-700 text-white hover:bg-blue-900">Create</button>
            <button type="button" onClick={() => setShowForm(false)} className="px-5 py-2 text-sm font-semibold border border-zinc-300 hover:bg-zinc-100">Cancel</button>
          </div>
        </form>
      )}

      <div className="space-y-4">
        {assignments.length === 0 && <p className="text-sm text-zinc-500" data-testid="assignments-empty-state">No assignments yet.</p>}
        {assignments.map((a) => (
          <div key={a.id} className="border border-zinc-200 p-6" data-testid={`assignment-${a.id}`}>
            <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
              <div className="flex gap-4 min-w-0">
                <div className="shrink-0 w-11 h-11 bg-zinc-100 flex items-center justify-center">
                  <ClipboardList className="w-5 h-5 text-blue-700" />
                </div>
                <div className="min-w-0">
                  <span className="text-xs uppercase tracking-[0.15em] font-semibold text-blue-700">{a.subject}</span>
                  <h3 className="font-heading font-bold mt-0.5">{a.title}</h3>
                  <p className="text-xs text-zinc-500 mt-1">{a.description}</p>
                  <div className="flex gap-4 text-xs text-zinc-500 mt-2">
                    {a.due_date && <span>Due {dayjs(a.due_date).format("D MMM YYYY")}</span>}
                    <span>{a.max_marks} marks</span>
                    <span>by {a.teacher_name}</span>
                  </div>
                </div>
              </div>
              <div className="shrink-0 flex items-center gap-2">
                {isTeacher ? (
                  <>
                    <button onClick={() => (viewSubsFor === a.id ? setViewSubsFor(null) : openSubmissions(a.id))} data-testid={`view-submissions-${a.id}`} className="px-4 py-2 text-sm font-semibold border border-zinc-300 hover:bg-zinc-100 transition-colors">
                      {a.submission_count} submissions
                    </button>
                    <button onClick={() => remove(a.id)} data-testid={`delete-assignment-${a.id}`} className="p-2 border border-zinc-300 text-zinc-500 hover:text-red-600 hover:border-red-300 transition-colors">
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </>
                ) : a.my_submission ? (
                  a.my_submission.grade != null ? (
                    <div className="border border-green-200 bg-green-50 px-4 py-2 text-sm" data-testid={`assignment-grade-${a.id}`}>
                      <span className="font-bold text-green-700">{a.my_submission.grade} / {a.max_marks}</span>
                      {a.my_submission.feedback && <p className="text-xs text-green-700 mt-0.5">"{a.my_submission.feedback}"</p>}
                    </div>
                  ) : (
                    <span className="border border-zinc-200 bg-zinc-50 px-4 py-2 text-sm font-semibold text-zinc-500" data-testid={`assignment-submitted-${a.id}`}>Submitted — awaiting grade</span>
                  )
                ) : (
                  <button onClick={() => setSubmitFor(submitFor === a.id ? null : a.id)} data-testid={`submit-assignment-${a.id}`} className="px-4 py-2 text-sm font-semibold bg-blue-700 text-white hover:bg-blue-900 transition-colors">
                    Submit work
                  </button>
                )}
              </div>
            </div>

            {!isTeacher && submitFor === a.id && (
              <form onSubmit={submitWork} className="mt-5 border-t border-zinc-200 pt-5 space-y-3" data-testid="submission-form">
                <textarea data-testid="submission-content-input" required value={subForm.content} onChange={(e) => setSubForm({ ...subForm, content: e.target.value })} placeholder="Write your answer or notes here…" rows={3} className="w-full border border-zinc-300 px-3 py-2 text-sm" />
                <input data-testid="submission-link-input" value={subForm.link} onChange={(e) => setSubForm({ ...subForm, link: e.target.value })} placeholder="Link to your scanned work (Google Drive, etc.) — optional" className="w-full border border-zinc-300 px-3 py-2 text-sm" />
                <button data-testid="submission-submit-button" className="px-5 py-2 text-sm font-semibold bg-blue-700 text-white hover:bg-blue-900">Submit assignment</button>
              </form>
            )}

            {isTeacher && viewSubsFor === a.id && (
              <div className="mt-5 border-t border-zinc-200 pt-5 space-y-3">
                {submissions.length === 0 && <p className="text-sm text-zinc-500">No submissions yet.</p>}
                {submissions.map((s) => (
                  <div key={s.id} className="border border-zinc-200 p-4" data-testid={`submission-${s.id}`}>
                    <div className="flex justify-between items-start gap-3">
                      <div className="min-w-0">
                        <span className="font-semibold text-sm">{s.student_name}</span>
                        <span className="text-xs text-zinc-400 ml-2">{dayjs(s.submitted_at).format("D MMM, h:mm A")}</span>
                        <p className="text-sm text-zinc-600 mt-1">{s.content}</p>
                        {s.link && <a href={s.link} target="_blank" rel="noreferrer" className="text-xs text-blue-700 hover:underline">{s.link}</a>}
                      </div>
                      {s.grade != null && <span className="shrink-0 font-bold text-green-700 text-sm">{s.grade} / {a.max_marks}</span>}
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2 items-center">
                      <input data-testid={`grade-input-${s.id}`} type="number" min="0" max={a.max_marks} placeholder="Marks" value={grades[s.id]?.grade ?? ""} onChange={(e) => setGrades({ ...grades, [s.id]: { ...grades[s.id], grade: e.target.value } })} className="w-24 border border-zinc-300 px-2.5 py-1.5 text-sm" />
                      <input data-testid={`feedback-input-${s.id}`} placeholder="Feedback (optional)" value={grades[s.id]?.feedback ?? ""} onChange={(e) => setGrades({ ...grades, [s.id]: { ...grades[s.id], feedback: e.target.value } })} className="flex-1 min-w-40 border border-zinc-300 px-2.5 py-1.5 text-sm" />
                      <button onClick={() => grade(s.id)} data-testid={`grade-button-${s.id}`} className="px-4 py-1.5 text-sm font-semibold border border-zinc-300 hover:bg-zinc-100">
                        {s.grade != null ? "Update grade" : "Grade"}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
