import { useEffect, useState, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { PlayCircle, FileText, CheckCircle2, Circle, Plus, Users, ArrowLeft } from "lucide-react";

export default function CourseDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const [course, setCourse] = useState(null);
  const [students, setStudents] = useState([]);
  const [sectionTitle, setSectionTitle] = useState("");
  const [lessonForms, setLessonForms] = useState({});

  const isOwner = user.role !== "student";

  const load = useCallback(() => {
    api.get(`/courses/${id}`).then((r) => setCourse(r.data));
    if (user.role !== "student") api.get(`/courses/${id}/students`).then((r) => setStudents(r.data));
  }, [id, user.role]);
  useEffect(load, [load]);

  if (!course) return <p className="text-sm text-zinc-500">Loading course…</p>;

  const enroll = async () => {
    try {
      await api.post(`/courses/${id}/enroll`);
      toast.success("Enrolled successfully");
      load();
    } catch (e) {
      toast.error(formatApiError(e));
    }
  };

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
                    <a href={lesson.url || "#"} target="_blank" rel="noreferrer" className="text-sm font-medium hover:text-blue-700 hover:underline">{lesson.title}</a>
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
              <div className="px-5 py-3 bg-zinc-50 border-t border-zinc-200 grid sm:grid-cols-5 gap-2">
                <input data-testid={`lesson-title-input-${section.id}`} value={lessonForms[section.id]?.title || ""} onChange={(e) => setLF(section.id, "title", e.target.value)} placeholder="Lesson title" className="sm:col-span-2 border border-zinc-300 px-2.5 py-1.5 text-sm" />
                <select value={lessonForms[section.id]?.type || "video"} onChange={(e) => setLF(section.id, "type", e.target.value)} className="border border-zinc-300 px-2 py-1.5 text-sm bg-white">
                  <option value="video">Video</option>
                  <option value="pdf">PDF / Notes</option>
                </select>
                <input value={lessonForms[section.id]?.url || ""} onChange={(e) => setLF(section.id, "url", e.target.value)} placeholder="URL" className="border border-zinc-300 px-2.5 py-1.5 text-sm" />
                <button type="button" onClick={() => addLesson(section.id)} data-testid={`add-lesson-button-${section.id}`} className="px-3 py-1.5 text-sm font-semibold border border-zinc-300 bg-white hover:bg-zinc-100">
                  Add lesson
                </button>
              </div>
            )}
          </div>
        ))}
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
    </div>
  );
}
