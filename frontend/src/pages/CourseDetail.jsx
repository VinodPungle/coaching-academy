import { useEffect, useState, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { api, formatApiError, uploadFile, fileUrl } from "@/lib/api";
import EnrollModal from "@/components/EnrollModal";
import VideoPlayerModal from "@/components/VideoPlayerModal";
import { toast } from "sonner";
import { PlayCircle, FileText, CheckCircle2, Circle, Plus, Users, ArrowLeft, Upload, Trash2, Radio, FileQuestion, ClipboardList } from "lucide-react";
import dayjs from "dayjs";

export default function CourseDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const [course, setCourse] = useState(null);
  const [students, setStudents] = useState([]);
  const [sectionTitle, setSectionTitle] = useState("");
  const [lessonForms, setLessonForms] = useState({});
  const [showEnroll, setShowEnroll] = useState(false);
  const [playerLesson, setPlayerLesson] = useState(null);
  const [batches, setBatches] = useState([]);
  const [batchForm, setBatchForm] = useState({ name: "", start_date: "", schedule: "", capacity: "" });
  const [uploadingFor, setUploadingFor] = useState(null);
  const [liveClasses, setLiveClasses] = useState([]);
  const [tests, setTests] = useState([]);
  const [assignments, setAssignments] = useState([]);

  const isOwner = user.role !== "student";

  const load = useCallback(() => {
    api.get(`/courses/${id}`).then((r) => setCourse(r.data));
    api.get(`/courses/${id}/batches`).then((r) => setBatches(r.data));
    api.get(`/live-classes`, { params: { course_id: id } }).then((r) => setLiveClasses(r.data)).catch(() => {});
    api.get(`/tests`).then((r) => setTests(r.data.filter((t) => t.course_id === id))).catch(() => {});
    api.get(`/assignments`).then((r) => setAssignments(r.data.filter((a) => a.course_id === id))).catch(() => {});
    if (user.role !== "student") api.get(`/courses/${id}/students`).then((r) => setStudents(r.data));
  }, [id, user.role]);
  useEffect(load, [load]);

  if (!course) return <p className="text-sm text-zinc-500">Loading course…</p>;

  const enroll = () => setShowEnroll(true);

  const toggleComplete = async (lessonId) => {
    if (course.completed_lessons.includes(lessonId)) return;
    await api.post(`/courses/${id}/lessons/${lessonId}/complete`);
    load();
  };

  const addSection = async (e) => {
    e.preventDefault();
    if (!sectionTitle.trim()) return;
    await api.post(`/courses/${id}/sections`, { title: sectionTitle });
    setSectionTitle("");
    toast.success("Section added");
    load();
  };

  const addLesson = async (sectionId) => {
    const f = lessonForms[sectionId];
    if (!f?.title) return;
    await api.post(`/courses/${id}/sections/${sectionId}/lessons`, f);
    setLessonForms({ ...lessonForms, [sectionId]: { title: "", type: "video", url: "", duration: "" } });
    toast.success("Lesson added");
    load();
  };

  const addBatch = async (e) => {
    e.preventDefault();
    if (!batchForm.name.trim()) return;
    try {
      await api.post(`/courses/${id}/batches`, { ...batchForm, capacity: batchForm.capacity ? Number(batchForm.capacity) : null });
      setBatchForm({ name: "", start_date: "", schedule: "", capacity: "" });
      toast.success("Batch created");
      load();
    } catch (err) {
      toast.error(formatApiError(err));
    }
  };

  const removeBatch = async (batchId) => {
    await api.delete(`/batches/${batchId}`);
    toast.success("Batch deleted");
    load();
  };

  const handleLessonFile = async (sectionId, file) => {
    if (!file) return;
    setUploadingFor(sectionId);
    try {
      const res = await uploadFile(file);
      setLessonForms((prev) => ({
        ...prev,
        [sectionId]: { title: "", duration: "", ...prev[sectionId], url: res.url, type: "pdf" },
      }));
      toast.success(`Uploaded ${res.filename}`);
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setUploadingFor(null);
    }
  };

  const setLF = (sid, k, v) =>
    setLessonForms({ ...lessonForms, [sid]: { title: "", type: "video", url: "", duration: "", ...lessonForms[sid], [k]: v } });

  const totalLessons = course.sections.reduce((n, s) => n + s.lessons.length, 0);
  const progress = totalLessons ? Math.round((course.completed_lessons.length / totalLessons) * 100) : 0;

  return (
    <div className="space-y-8">
      <Link to="/app/courses" className="inline-flex items-center gap-1.5 text-sm text-zinc-500 hover:text-zinc-950" data-testid="back-to-courses">
        <ArrowLeft className="w-4 h-4" /> Back to courses
      </Link>
      <div className="flex flex-col md:flex-row gap-6 md:items-start justify-between">
        <div className="max-w-2xl">
          <span className="text-xs uppercase tracking-[0.2em] font-semibold text-blue-700">{course.subject}</span>
          <h1 className="font-heading text-3xl font-black tracking-tight mt-1" data-testid="course-detail-title">{course.title}</h1>
          <p className="text-sm text-zinc-500 mt-3 leading-relaxed">{course.description}</p>
          <div className="flex gap-6 text-sm text-zinc-500 mt-4">
            <span>Instructor: <span className="font-semibold text-zinc-950">{course.teacher_name}</span></span>
            <span>{course.duration}</span>
            <span className="inline-flex items-center gap-1"><Users className="w-4 h-4" />{course.enrolled_count} enrolled</span>
          </div>
        </div>
        {!isOwner && !course.enrolled && (
          <button onClick={enroll} data-testid="course-detail-enroll-button" className="shrink-0 px-6 py-3 bg-blue-700 text-white font-semibold hover:bg-blue-900 transition-colors">
            Enroll now — ₹{course.price}
          </button>
        )}
        {!isOwner && course.enrolled && (
          <div className="shrink-0 border border-zinc-200 p-4 w-48">
            <div className="flex justify-between text-xs text-zinc-500 mb-1.5"><span>Progress</span><span className="font-semibold text-zinc-950">{progress}%</span></div>
            <div className="h-1.5 bg-zinc-100"><div className="h-full bg-blue-700" style={{ width: `${progress}%` }} /></div>
            {course.my_batch && (
              <p className="mt-3 text-xs text-zinc-500" data-testid="my-batch-info">
                Batch: <span className="font-semibold text-zinc-950">{course.my_batch.name}</span>
                {course.my_batch.schedule && <span className="block mt-0.5">{course.my_batch.schedule}</span>}
              </p>
            )}
            {progress === 100 && (
              <Link to={`/certificate/${course.id}`} data-testid="course-certificate-link" className="mt-3 block text-center py-2 text-xs font-semibold bg-zinc-950 text-white hover:bg-zinc-800 transition-colors">
                View certificate
              </Link>
            )}
          </div>
        )}
      </div>

      {isOwner && (
        <form onSubmit={addSection} className="flex gap-2">
          <input
            data-testid="new-section-input"
            value={sectionTitle}
            onChange={(e) => setSectionTitle(e.target.value)}
            placeholder="New section title (e.g. Thermodynamics)"
            className="flex-1 max-w-md border border-zinc-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-700"
          />
          <button data-testid="add-section-button" className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-semibold bg-blue-700 text-white hover:bg-blue-900">
            <Plus className="w-4 h-4" /> Add section
          </button>
        </form>
      )}

      <div className="space-y-4">
        <h2 className="font-heading text-xl font-bold">Curriculum</h2>
        {course.sections.length === 0 && <p className="text-sm text-zinc-500">No content added yet.</p>}
        {course.sections.map((section, si) => (
          <div key={section.id} className="border border-zinc-200" data-testid={`section-${section.id}`}>
            <div className="px-5 py-3 bg-zinc-50 border-b border-zinc-200 font-semibold text-sm">
              {si + 1}. {section.title}
            </div>
            {section.lessons.map((lesson) => {
              const done = course.completed_lessons?.includes(lesson.id);
              return (
                <div key={lesson.id} className="px-5 py-3 border-b border-zinc-100 last:border-0 flex items-center gap-3" data-testid={`lesson-${lesson.id}`}>
                  {lesson.type === "video" ? <PlayCircle className="w-4 h-4 text-blue-700 shrink-0" /> : <FileText className="w-4 h-4 text-red-600 shrink-0" />}
                  <div className="flex-1 min-w-0">
                    {lesson.type === "video" ? (
                      <button
                        onClick={() => setPlayerLesson(lesson)}
                        data-testid={`play-lesson-${lesson.id}`}
                        className="text-sm font-medium text-left hover:text-blue-700 hover:underline"
                      >
                        {lesson.title}
                      </button>
                    ) : (
                      <a href={fileUrl(lesson.url) || "#"} target="_blank" rel="noreferrer" className="text-sm font-medium hover:text-blue-700 hover:underline">{lesson.title}</a>
                    )}
                    <span className="text-xs text-zinc-400 ml-2">{lesson.duration}</span>
                  </div>
                  {!isOwner && course.enrolled && (
                    <button onClick={() => toggleComplete(lesson.id)} data-testid={`complete-lesson-${lesson.id}`} title={done ? "Completed" : "Mark complete"}>
                      {done ? <CheckCircle2 className="w-5 h-5 text-green-600" /> : <Circle className="w-5 h-5 text-zinc-300 hover:text-blue-700" />}
                    </button>
                  )}
                </div>
              );
            })}
            {isOwner && (
              <div className="px-5 py-3 bg-zinc-50 border-t border-zinc-200 space-y-2">
                <div className="grid sm:grid-cols-5 gap-2">
                  <input data-testid={`lesson-title-input-${section.id}`} value={lessonForms[section.id]?.title || ""} onChange={(e) => setLF(section.id, "title", e.target.value)} placeholder="Lesson title" className="sm:col-span-2 border border-zinc-300 px-2.5 py-1.5 text-sm" />
                  <select value={lessonForms[section.id]?.type || "video"} onChange={(e) => setLF(section.id, "type", e.target.value)} className="border border-zinc-300 px-2 py-1.5 text-sm bg-white">
                    <option value="video">Video</option>
                    <option value="pdf">PDF / Notes</option>
                  </select>
                  <input value={lessonForms[section.id]?.url || ""} onChange={(e) => setLF(section.id, "url", e.target.value)} placeholder="URL or upload →" className="border border-zinc-300 px-2.5 py-1.5 text-sm" />
                  <button type="button" onClick={() => addLesson(section.id)} data-testid={`add-lesson-button-${section.id}`} className="px-3 py-1.5 text-sm font-semibold border border-zinc-300 bg-white hover:bg-zinc-100">
                    Add lesson
                  </button>
                </div>
                <label className="inline-flex items-center gap-2 text-xs font-semibold text-blue-700 cursor-pointer hover:underline">
                  <Upload className="w-3.5 h-3.5" />
                  {uploadingFor === section.id ? "Uploading…" : "Upload notes file (PDF, DOCX, images — max 25 MB)"}
                  <input type="file" data-testid={`lesson-file-input-${section.id}`} className="hidden" accept=".pdf,.doc,.docx,.png,.jpg,.jpeg,.webp,.txt,.pptx,.xlsx,.zip,.csv" onChange={(e) => handleLessonFile(section.id, e.target.files?.[0])} />
                </label>
              </div>
            )}
          </div>
        ))}
      </div>

      {isOwner && (
        <div className="space-y-3">
          <h2 className="font-heading text-xl font-bold">Batches ({batches.length})</h2>
          <form onSubmit={addBatch} className="border border-zinc-200 p-5 grid sm:grid-cols-5 gap-2 items-end">
            <div className="sm:col-span-2">
              <label className="text-xs uppercase tracking-[0.15em] font-semibold text-zinc-500">Batch name</label>
              <input data-testid="batch-name-input" value={batchForm.name} onChange={(e) => setBatchForm({ ...batchForm, name: e.target.value })} placeholder="Weekend Batch" className="mt-1 w-full border border-zinc-300 px-2.5 py-1.5 text-sm" />
            </div>
            <div>
              <label className="text-xs uppercase tracking-[0.15em] font-semibold text-zinc-500">Start date</label>
              <input data-testid="batch-start-input" type="date" value={batchForm.start_date} onChange={(e) => setBatchForm({ ...batchForm, start_date: e.target.value })} className="mt-1 w-full border border-zinc-300 px-2.5 py-1.5 text-sm" />
            </div>
            <div>
              <label className="text-xs uppercase tracking-[0.15em] font-semibold text-zinc-500">Schedule</label>
              <input data-testid="batch-schedule-input" value={batchForm.schedule} onChange={(e) => setBatchForm({ ...batchForm, schedule: e.target.value })} placeholder="Sat–Sun, 10 AM" className="mt-1 w-full border border-zinc-300 px-2.5 py-1.5 text-sm" />
            </div>
            <div className="flex gap-2">
              <div className="flex-1">
                <label className="text-xs uppercase tracking-[0.15em] font-semibold text-zinc-500">Capacity</label>
                <input data-testid="batch-capacity-input" type="number" min="1" value={batchForm.capacity} onChange={(e) => setBatchForm({ ...batchForm, capacity: e.target.value })} placeholder="50" className="mt-1 w-full border border-zinc-300 px-2.5 py-1.5 text-sm" />
              </div>
              <button data-testid="add-batch-button" className="self-end px-4 py-1.5 text-sm font-semibold bg-blue-700 text-white hover:bg-blue-900">Add</button>
            </div>
          </form>
          {batches.length > 0 && (
            <div className="border border-zinc-200 overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-zinc-50 text-left text-xs uppercase tracking-[0.1em] text-zinc-500">
                  <tr>
                    <th className="px-5 py-3 font-semibold">Batch</th>
                    <th className="px-5 py-3 font-semibold">Schedule</th>
                    <th className="px-5 py-3 font-semibold">Starts</th>
                    <th className="px-5 py-3 font-semibold">Students</th>
                    <th className="px-5 py-3"></th>
                  </tr>
                </thead>
                <tbody>
                  {batches.map((b) => (
                    <tr key={b.id} className="border-t border-zinc-100" data-testid={`batch-row-${b.id}`}>
                      <td className="px-5 py-3 font-medium">{b.name}</td>
                      <td className="px-5 py-3 text-zinc-500">{b.schedule || "—"}</td>
                      <td className="px-5 py-3 text-zinc-500">{b.start_date || "—"}</td>
                      <td className="px-5 py-3">{b.enrolled_count}{b.capacity ? ` / ${b.capacity}` : ""}</td>
                      <td className="px-5 py-3 text-right">
                        <button onClick={() => removeBatch(b.id)} data-testid={`delete-batch-${b.id}`} className="p-1.5 text-zinc-400 hover:text-red-600">
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Cross-linked content: live classes, tests, assignments for this course */}
      <div className="grid md:grid-cols-3 gap-4" data-testid="course-linked-content">
        <LinkedList
          title="Live Classes"
          icon={Radio}
          testid="linked-live-classes"
          empty="No live classes scheduled for this course yet."
          items={liveClasses}
          renderItem={(c) => {
            const past = c.start_time < new Date().toISOString();
            return (
              <div className="text-sm">
                <div className="font-semibold">{c.title}</div>
                <div className="text-xs text-zinc-500 mt-0.5">
                  {dayjs(c.start_time).format("D MMM, h:mm A")} · {past ? "past" : "upcoming"}
                  {c.batch_name && ` · ${c.batch_name}`}
                </div>
              </div>
            );
          }}
          viewAllTo="/app/live"
        />
        <LinkedList
          title="Tests"
          icon={FileQuestion}
          testid="linked-tests"
          empty="No tests linked to this course yet."
          items={tests}
          renderItem={(t) => (
            <div className="text-sm">
              <div className="font-semibold">{t.title}</div>
              <div className="text-xs text-zinc-500 mt-0.5">{t.subject} · {t.questions?.length ?? 0} Qs · {t.duration_min} min</div>
            </div>
          )}
          viewAllTo="/app/tests"
        />
        <LinkedList
          title="Assignments"
          icon={ClipboardList}
          testid="linked-assignments"
          empty="No assignments linked to this course yet."
          items={assignments}
          renderItem={(a) => (
            <div className="text-sm">
              <div className="font-semibold">{a.title}</div>
              <div className="text-xs text-zinc-500 mt-0.5">
                {a.subject}{a.due_date ? ` · Due ${dayjs(a.due_date).format("D MMM")}` : ""}
              </div>
            </div>
          )}
          viewAllTo="/app/assignments"
        />
      </div>

      {isOwner && (
        <div className="space-y-3">
          <h2 className="font-heading text-xl font-bold">Enrolled Students ({students.length})</h2>
          {students.length === 0 ? (
            <p className="text-sm text-zinc-500">No students enrolled yet.</p>
          ) : (
            <div className="border border-zinc-200 overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-zinc-50 text-left text-xs uppercase tracking-[0.1em] text-zinc-500">
                  <tr>
                    <th className="px-5 py-3 font-semibold">Name</th>
                    <th className="px-5 py-3 font-semibold">Email</th>
                    <th className="px-5 py-3 font-semibold">Lessons completed</th>
                  </tr>
                </thead>
                <tbody>
                  {students.map((s) => (
                    <tr key={s.id} className="border-t border-zinc-100">
                      <td className="px-5 py-3 font-medium">{s.name}</td>
                      <td className="px-5 py-3 text-zinc-500">{s.email}</td>
                      <td className="px-5 py-3">{s.completed_lessons} / {totalLessons}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
      {showEnroll && (
        <EnrollModal
          course={course}
          onClose={() => setShowEnroll(false)}
          onSuccess={() => { setShowEnroll(false); load(); }}
        />
      )}
      {playerLesson && (
        <VideoPlayerModal
          lesson={playerLesson}
          completed={course.completed_lessons?.includes(playerLesson.id)}
          canComplete={!isOwner && course.enrolled}
          onComplete={async () => {
            await api.post(`/courses/${id}/lessons/${playerLesson.id}/complete`);
            toast.success("Lesson marked complete");
            load();
          }}
          onClose={() => setPlayerLesson(null)}
        />
      )}
    </div>
  );
}

function LinkedList({ title, icon: Icon, testid, items, renderItem, empty, viewAllTo }) {
  return (
    <div className="border border-zinc-200" data-testid={testid}>
      <div className="px-4 py-3 border-b border-zinc-200 bg-zinc-50 flex items-center gap-2">
        <Icon className="w-4 h-4 text-blue-700" />
        <h3 className="font-heading font-bold text-sm">{title}</h3>
        <span className="ml-auto text-xs font-semibold text-zinc-500">{items.length}</span>
      </div>
      {items.length === 0 ? (
        <p className="px-4 py-6 text-xs text-zinc-400">{empty}</p>
      ) : (
        <ul className="divide-y divide-zinc-100 max-h-64 overflow-auto">
          {items.slice(0, 6).map((it, i) => (
            <li key={it.id || i} className="px-4 py-2.5">{renderItem(it)}</li>
          ))}
        </ul>
      )}
      {viewAllTo && items.length > 0 && (
        <Link to={viewAllTo} className="block text-center px-4 py-2 border-t border-zinc-200 text-xs font-semibold text-blue-700 hover:bg-zinc-50">
          View all →
        </Link>
      )}
    </div>
  );
}
