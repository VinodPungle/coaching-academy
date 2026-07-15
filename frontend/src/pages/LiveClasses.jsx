import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Radio, Plus, Trash2, ExternalLink, Clock, Calendar, Video, Play, Users } from "lucide-react";
import dayjs from "dayjs";

// Ensure link opens externally, not as a relative SPA route
const normalizeUrl = (url) => {
  if (!url) return "";
  const trimmed = String(url).trim();
  if (!trimmed) return "";
  if (/^https?:\/\//i.test(trimmed)) return trimmed;
  // Strip a leading slash then prepend https://
  return `https://${trimmed.replace(/^\/+/, "")}`;
};

export default function LiveClasses() {
  const { user } = useAuth();
  const [classes, setClasses] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [teacherCourses, setTeacherCourses] = useState([]);
  const [batches, setBatches] = useState([]);
  const [zoomReady, setZoomReady] = useState(false);
  const [form, setForm] = useState({ title: "", subject: "Physics", description: "", start_time: "", duration_min: 60, meeting_link: "", course_id: "", batch_id: "", create_zoom: false });

  const isTeacher = user.role !== "student";
  const load = () => api.get("/live-classes").then((r) => setClasses(r.data));
  useEffect(() => {
    load();
    if (user.role !== "student") {
      api.get("/teacher/courses").then((r) => setTeacherCourses(r.data));
      api.get("/zoom/config").then((r) => setZoomReady(r.data.configured)).catch(() => {});
    }
  }, []);

  const onCourseChange = (courseId) => {
    setForm({ ...form, course_id: courseId, batch_id: "" });
    setBatches([]);
    if (courseId) api.get(`/courses/${courseId}/batches`).then((r) => setBatches(r.data));
  };

  const create = async (e) => {
    e.preventDefault();
    try {
      await api.post("/live-classes", {
        ...form,
        course_id: form.course_id || null,
        batch_id: form.batch_id || null,
        duration_min: Number(form.duration_min),
        start_time: new Date(form.start_time).toISOString(),
      });
      toast.success("Live class scheduled");
      setShowForm(false);
      setForm({ title: "", subject: "Physics", description: "", start_time: "", duration_min: 60, meeting_link: "", course_id: "", batch_id: "", create_zoom: false });
      load();
    } catch (err) {
      toast.error(formatApiError(err));
    }
  };

  const remove = async (id) => {
    if (!window.confirm("Delete this class permanently?")) return;
    await api.delete(`/live-classes/${id}`);
    toast.success("Class deleted");
    load();
  };

  const reschedule = async (id, currentStart) => {
    const input = window.prompt("New start time (YYYY-MM-DD HH:mm):", dayjs(currentStart).format("YYYY-MM-DD HH:mm"));
    if (!input) return;
    const iso = new Date(input.replace(" ", "T")).toISOString();
    try {
      await api.put(`/live-classes/${id}/reschedule`, { start_time: iso });
      toast.success("Class rescheduled");
      load();
    } catch (err) { toast.error(formatApiError(err)); }
  };

  const setRecording = async (id, current) => {
    const url = window.prompt("Recording URL (YouTube / Drive / Zoom cloud):", current || "");
    if (url === null) return;
    try {
      if (url.trim()) {
        await api.put(`/live-classes/${id}/recording`, { recording_url: url.trim() });
        toast.success("Recording attached");
      } else {
        await api.delete(`/live-classes/${id}/recording`);
        toast.success("Recording removed");
      }
      load();
    } catch (err) { toast.error(formatApiError(err)); }
  };

  const joinAsStudent = async (id, link) => {
    try {
      await api.post(`/live-classes/${id}/attend`);
    } catch (err) { toast.error(formatApiError(err)); return; }
    window.open(normalizeUrl(link), "_blank", "noopener,noreferrer");
  };

  // A class is "in progress" during [start_time, start_time + duration_min].
  // It moves to "past" only after the full duration has elapsed.
  const nowMs = Date.now();
  const classEndMs = (c) => new Date(c.start_time).getTime() + (Number(c.duration_min) || 0) * 60_000;
  const isInProgress = (c) => new Date(c.start_time).getTime() <= nowMs && nowMs < classEndMs(c);
  const isUpcomingOrLive = (c) => classEndMs(c) > nowMs;
  const upcoming = classes.filter(isUpcomingOrLive);
  const past = classes.filter((c) => classEndMs(c) <= nowMs);

  const ClassRow = ({ c, isPast }) => {
    const live = !isPast && isInProgress(c);
    return (
    <div className="border border-zinc-200 p-5 flex flex-col sm:flex-row sm:items-center gap-4 hover:border-zinc-300 transition-colors" data-testid={`live-class-${c.id}`}>
      <div className={`shrink-0 w-12 h-12 flex items-center justify-center ${isPast ? "bg-zinc-100 text-zinc-400" : live ? "bg-red-600 text-white animate-pulse" : "bg-red-50 text-red-600"}`}>
        <Radio className="w-5 h-5" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs uppercase tracking-[0.15em] font-semibold text-blue-700">{c.subject}</span>
          {live && <span data-testid={`class-live-badge-${c.id}`} className="text-[10px] uppercase tracking-[0.15em] font-bold bg-red-600 text-white px-1.5 py-0.5 animate-pulse">Live now</span>}
          {!isPast && !live && <span className="text-[10px] uppercase tracking-[0.15em] font-bold bg-red-600 text-white px-1.5 py-0.5">Upcoming</span>}
          {c.course_name ? (
            <span className="text-[10px] uppercase tracking-[0.1em] font-bold bg-zinc-950 text-white px-1.5 py-0.5" data-testid={`class-scope-badge-${c.id}`}>
              {c.course_name}{c.batch_name ? ` · ${c.batch_name}` : ""}
            </span>
          ) : (
            <span className="text-[10px] uppercase tracking-[0.1em] font-bold bg-blue-50 text-blue-700 border border-blue-200 px-1.5 py-0.5" data-testid={`class-all-badge-${c.id}`}>For all students</span>
          )}
        </div>
        <h3 className="font-heading font-bold mt-0.5">{c.title}</h3>
        <p className="text-xs text-zinc-500 mt-1">{c.description}</p>
        <div className="flex items-center gap-4 text-xs text-zinc-500 mt-2">
          <span className="inline-flex items-center gap-1"><Clock className="w-3.5 h-3.5" />{dayjs(c.start_time).format("ddd, D MMM YYYY · h:mm A")}</span>
          <span>{c.duration_min} min</span>
          <span>by {c.teacher_name}</span>
        </div>
      </div>
      <div className="flex items-center gap-2 shrink-0 flex-wrap">
        {isPast && c.recording_url ? (
          <Link to={`/app/live/${c.id}/recording`} data-testid={`view-recording-${c.id}`} className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-semibold bg-zinc-950 text-white hover:bg-zinc-800 transition-colors">
            View recording <Play className="w-3.5 h-3.5" />
          </Link>
        ) : !isPast && c.meeting_link ? (
          user.role === "student" ? (
            <button onClick={() => joinAsStudent(c.id, c.meeting_link)} data-testid={`join-class-${c.id}`} className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-semibold bg-blue-700 text-white hover:bg-blue-900 transition-colors">
              Join class <ExternalLink className="w-3.5 h-3.5" />
            </button>
          ) : (
            <a href={normalizeUrl(c.meeting_link)} target="_blank" rel="noopener noreferrer" data-testid={`join-class-${c.id}`} className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-semibold bg-blue-700 text-white hover:bg-blue-900 transition-colors">
              Join class <ExternalLink className="w-3.5 h-3.5" />
            </a>
          )
        ) : null}
        {isTeacher && (
          <>
            {!isPast && (
              <button onClick={() => reschedule(c.id, c.start_time)} data-testid={`reschedule-class-${c.id}`} className="p-2 border border-zinc-300 text-zinc-600 hover:text-blue-700 hover:border-blue-300 transition-colors" title="Reschedule">
                <Calendar className="w-4 h-4" />
              </button>
            )}
            <button onClick={() => setRecording(c.id, c.recording_url)} data-testid={`recording-class-${c.id}`} className={`p-2 border transition-colors ${c.recording_url ? "border-blue-300 text-blue-700 bg-blue-50" : "border-zinc-300 text-zinc-500 hover:text-blue-700 hover:border-blue-300"}`} title={c.recording_url ? "Recording attached" : "Attach recording"}>
              <Video className="w-4 h-4" />
            </button>
            <Link to={`/app/live/${c.id}/attendance`} data-testid={`attendance-class-${c.id}`} className="p-2 border border-zinc-300 text-zinc-500 hover:text-zinc-950 hover:border-zinc-500 transition-colors" title="Attendance">
              <Users className="w-4 h-4" />
            </Link>
            <button onClick={() => remove(c.id)} data-testid={`delete-class-${c.id}`} className="p-2 border border-zinc-300 text-zinc-500 hover:text-red-600 hover:border-red-300 transition-colors">
              <Trash2 className="w-4 h-4" />
            </button>
          </>
        )}
      </div>
    </div>
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between flex-wrap gap-4">
        <h1 className="font-heading text-3xl font-black tracking-tight">Live Classes</h1>
        {isTeacher && (
          <button onClick={() => setShowForm(!showForm)} data-testid="schedule-class-button" className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-semibold bg-blue-700 text-white hover:bg-blue-900 transition-colors">
            <Plus className="w-4 h-4" /> Schedule class
          </button>
        )}
      </div>

      {isTeacher && showForm && (
        <form onSubmit={create} className="border border-zinc-200 p-6 grid sm:grid-cols-2 gap-4" data-testid="schedule-class-form">
          <div className="sm:col-span-2">
            <label className="text-xs uppercase tracking-[0.15em] font-semibold text-zinc-500">Title</label>
            <input data-testid="class-title-input" required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} className="mt-1 w-full border border-zinc-300 px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="text-xs uppercase tracking-[0.15em] font-semibold text-zinc-500">Subject</label>
            <select value={form.subject} onChange={(e) => setForm({ ...form, subject: e.target.value })} className="mt-1 w-full border border-zinc-300 px-3 py-2 text-sm bg-white">
              {["Physics", "Chemistry", "Mathematics", "Biotechnology"].map((s) => <option key={s}>{s}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs uppercase tracking-[0.15em] font-semibold text-zinc-500">Start time</label>
            <input data-testid="class-start-input" type="datetime-local" required value={form.start_time} onChange={(e) => setForm({ ...form, start_time: e.target.value })} className="mt-1 w-full border border-zinc-300 px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="text-xs uppercase tracking-[0.15em] font-semibold text-zinc-500">Duration (min)</label>
            <input type="number" value={form.duration_min} onChange={(e) => setForm({ ...form, duration_min: e.target.value })} className="mt-1 w-full border border-zinc-300 px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="text-xs uppercase tracking-[0.15em] font-semibold text-zinc-500">Meeting link</label>
            <input data-testid="class-link-input" value={form.meeting_link} onChange={(e) => setForm({ ...form, meeting_link: e.target.value })} placeholder="https://meet.google.com/…" disabled={form.create_zoom} className="mt-1 w-full border border-zinc-300 px-3 py-2 text-sm disabled:opacity-50" />
            <label className={`mt-2 flex items-center gap-2 text-xs font-semibold ${zoomReady ? "text-blue-700 cursor-pointer" : "text-zinc-400"}`}>
              <input
                type="checkbox"
                data-testid="class-create-zoom-checkbox"
                disabled={!zoomReady}
                checked={form.create_zoom}
                onChange={(e) => setForm({ ...form, create_zoom: e.target.checked, meeting_link: e.target.checked ? "" : form.meeting_link })}
                className="accent-blue-700"
              />
              Auto-create Zoom meeting{!zoomReady && " (Zoom credentials not configured yet)"}
            </label>
          </div>
          <div>
            <label className="text-xs uppercase tracking-[0.15em] font-semibold text-zinc-500">Course (optional)</label>
            <select data-testid="class-course-select" value={form.course_id} onChange={(e) => onCourseChange(e.target.value)} className="mt-1 w-full border border-zinc-300 px-3 py-2 text-sm bg-white">
              <option value="">All students</option>
              {teacherCourses.map((c) => <option key={c.id} value={c.id}>{c.title}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs uppercase tracking-[0.15em] font-semibold text-zinc-500">Batch (optional)</label>
            <select data-testid="class-batch-select" value={form.batch_id} onChange={(e) => setForm({ ...form, batch_id: e.target.value })} disabled={!form.course_id} className="mt-1 w-full border border-zinc-300 px-3 py-2 text-sm bg-white disabled:opacity-50">
              <option value="">All batches</option>
              {batches.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
            </select>
          </div>
          <div className="sm:col-span-2">
            <label className="text-xs uppercase tracking-[0.15em] font-semibold text-zinc-500">Description</label>
            <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} rows={2} className="mt-1 w-full border border-zinc-300 px-3 py-2 text-sm" />
          </div>
          <div className="sm:col-span-2 flex gap-2">
            <button data-testid="class-submit-button" className="px-5 py-2 text-sm font-semibold bg-blue-700 text-white hover:bg-blue-900">Schedule</button>
            <button type="button" onClick={() => setShowForm(false)} className="px-5 py-2 text-sm font-semibold border border-zinc-300 hover:bg-zinc-100">Cancel</button>
          </div>
        </form>
      )}

      <div className="space-y-3">
        {upcoming.length === 0 && <p className="text-sm text-zinc-500" data-testid="no-upcoming-classes">No upcoming or live classes.</p>}
        {upcoming.map((c) => <ClassRow key={c.id} c={c} isPast={false} />)}
      </div>
      {past.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-xs uppercase tracking-[0.2em] font-semibold text-zinc-500 pt-4">Past classes</h2>
          {past.map((c) => <ClassRow key={c.id} c={c} isPast />)}
        </div>
      )}
    </div>
  );
}
