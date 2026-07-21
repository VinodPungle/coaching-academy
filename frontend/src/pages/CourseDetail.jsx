// The single biggest page in the app — course detail AND course
// management live in one component, split by role: `isOwner` (teacher/
// admin) sees curriculum-editing controls, batches, enrolled-students
// table, and syllabus management; students see a read-only curriculum
// with progress tracking and enroll/certificate actions. Curriculum edits
// (sections/sub-topics/lessons, reordering, etc.) all call the nested
// endpoints in backend/routers/courses.py and reload the whole course
// afterward rather than optimistically patching local state.
import { useEffect, useState, useCallback } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { api, formatApiError, uploadFile, fileUrl } from "@/lib/api";
import { syllabusFileError } from "@/lib/syllabus";
import EnrollModal from "@/components/EnrollModal";
import { toast } from "sonner";
import {
  PlayCircle, FileText, CheckCircle2, Circle, Plus, Users, ArrowLeft, Upload, Trash2,
  Radio, FileQuestion, ClipboardList, ChevronDown, ChevronRight, Edit2, MessageSquare, MessageSquareOff, GripVertical,
} from "lucide-react";
import dayjs from "dayjs";

export default function CourseDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [course, setCourse] = useState(null);
  const [students, setStudents] = useState([]);
  const [sectionTitle, setSectionTitle] = useState("");
  const [showEnroll, setShowEnroll] = useState(false);
  const [batches, setBatches] = useState([]);
  const [batchForm, setBatchForm] = useState({ name: "", start_date: "", schedule: "", capacity: "" });
  const [liveClasses, setLiveClasses] = useState([]);
  const [tests, setTests] = useState([]);
  const [assignments, setAssignments] = useState([]);
  const [expandedSections, setExpandedSections] = useState({});
  const [expandedSubTopics, setExpandedSubTopics] = useState({});
  const [subTopicForm, setSubTopicForm] = useState({}); // { sectionId: {title} }
  const [renamingSubTopic, setRenamingSubTopic] = useState(null); // {sectionId, id, title}
  const [renamingSection, setRenamingSection] = useState(null); // {id, title}
  const [editingLesson, setEditingLesson] = useState(null); // {id, title, url, duration, notes, sectionId, subTopicId}
  const [lessonEditUploadingNotes, setLessonEditUploadingNotes] = useState(false);
  const [lessonEditUploadingVideo, setLessonEditUploadingVideo] = useState(false);
  const [lessonEditVideoProgress, setLessonEditVideoProgress] = useState(0);
  const [lessonForm, setLessonForm] = useState({}); // { subTopicId: {title, url, duration, notes: []} }
  const [uploadingFor, setUploadingFor] = useState(null);
  const [uploadingVideoFor, setUploadingVideoFor] = useState(null);
  const [videoProgress, setVideoProgress] = useState({}); // { subTopicId: pct }
  const [editingCourse, setEditingCourse] = useState(null); // {title, subject, description, duration, price, image_url, is_free}
  const [syllabusBusy, setSyllabusBusy] = useState(false);

  const isOwner = user.role !== "student";
  const canEditCourse = user.role === "teacher" && course && course.teacher_id === user.id;

  const load = useCallback(() => {
    api.get(`/courses/${id}`).then((r) => setCourse(r.data));
    api.get(`/courses/${id}/batches`).then((r) => setBatches(r.data));
    api.get(`/live-classes`, { params: { course_id: id } }).then((r) => setLiveClasses(r.data)).catch(() => {});
    api.get(`/tests`).then((r) => setTests(r.data.filter((t) => t.course_id === id))).catch(() => {});
    api.get(`/assignments`).then((r) => setAssignments(r.data.filter((a) => a.course_id === id))).catch(() => {});
    if (user.role !== "student") api.get(`/courses/${id}/students`).then((r) => setStudents(r.data));
  }, [id, user.role]);
  useEffect(load, [load]);

  if (!course) return <p className="text-sm text-zinc-500" data-testid="course-loading">Loading course…</p>;

  const totalLessons = course.sections.reduce(
    (n, s) => n + s.sub_topics.reduce((k, st) => k + st.lessons.length, 0), 0
  );
  const progress = totalLessons ? Math.round((course.completed_lessons.length / totalLessons) * 100) : 0;

  const toggleSection = (sid) => setExpandedSections({ ...expandedSections, [sid]: !expandedSections[sid] });
  const toggleSubTopic = (stid) => setExpandedSubTopics({ ...expandedSubTopics, [stid]: !expandedSubTopics[stid] });

  const toggleComplete = async (lessonId) => {
    if (course.completed_lessons.includes(lessonId)) return;
    await api.post(`/courses/${id}/lessons/${lessonId}/complete`);
    load();
  };

  const addSection = async (e) => {
    e.preventDefault();
    if (!sectionTitle.trim()) return;
    try {
      await api.post(`/courses/${id}/sections`, { title: sectionTitle });
      setSectionTitle("");
      toast.success("Section added");
      load();
    } catch (err) { toast.error(formatApiError(err)); }
  };

  const deleteSection = async (sid) => {
    if (!window.confirm("Delete this entire section and all its sub-topics/lessons?")) return;
    try {
      await api.delete(`/courses/${id}/sections/${sid}`);
      toast.success("Section deleted");
      load();
    } catch (err) { toast.error(formatApiError(err)); }
  };

  const renameSection = async () => {
    if (!renamingSection) return;
    const title = (renamingSection.title || "").trim();
    if (!title) { setRenamingSection(null); return; }
    try {
      await api.put(`/courses/${id}/sections/${renamingSection.id}`, { title });
      setRenamingSection(null);
      toast.success("Section renamed");
      load();
    } catch (err) { toast.error(formatApiError(err)); }
  };

  const addSubTopic = async (sid) => {
    const title = (subTopicForm[sid] || "").trim();
    if (!title) return toast.error("Sub topic title is required");
    try {
      await api.post(`/courses/${id}/sections/${sid}/sub-topics`, { title });
      setSubTopicForm({ ...subTopicForm, [sid]: "" });
      toast.success("Sub topic added");
      load();
    } catch (err) { toast.error(formatApiError(err)); }
  };

  const renameSubTopic = async () => {
    if (!renamingSubTopic) return;
    try {
      await api.put(
        `/courses/${id}/sections/${renamingSubTopic.sectionId}/sub-topics/${renamingSubTopic.id}`,
        { title: renamingSubTopic.title }
      );
      setRenamingSubTopic(null);
      toast.success("Sub topic renamed");
      load();
    } catch (err) { toast.error(formatApiError(err)); }
  };

  const deleteSubTopic = async (sid, stid) => {
    if (!window.confirm("Delete this sub topic?")) return;
    try {
      await api.delete(`/courses/${id}/sections/${sid}/sub-topics/${stid}`);
      toast.success("Sub topic deleted");
      load();
    } catch (err) { toast.error(formatApiError(err)); }
  };

  const reorderSubTopic = async (sid, subTopics, fromIdx, direction) => {
    const newOrder = [...subTopics];
    const swapWith = direction === "up" ? fromIdx - 1 : fromIdx + 1;
    if (swapWith < 0 || swapWith >= newOrder.length) return;
    [newOrder[fromIdx], newOrder[swapWith]] = [newOrder[swapWith], newOrder[fromIdx]];
    try {
      await api.put(
        `/courses/${id}/sections/${sid}/sub-topics/reorder`,
        { sub_topic_ids: newOrder.map((s) => s.id) }
      );
      load();
    } catch (err) { toast.error(formatApiError(err)); }
  };

  const toggleSubTopicComments = async (sid, stid, current) => {
    try {
      await api.put(
        `/courses/${id}/sections/${sid}/sub-topics/${stid}/comments-toggle`,
        { comments_enabled: !current }
      );
      toast.success(`Comments ${!current ? "enabled" : "disabled"}`);
      load();
    } catch (err) { toast.error(formatApiError(err)); }
  };

  const setLF = (stid, patch) =>
    setLessonForm({ ...lessonForm, [stid]: { title: "", url: "", duration: "", notes: [], ...lessonForm[stid], ...patch } });

  const handleNotesFile = async (stid, file) => {
    if (!file) return;
    setUploadingFor(stid);
    try {
      const res = await uploadFile(file);
      setLF(stid, { notes: [...(lessonForm[stid]?.notes || []), { title: res.filename, url: res.url }] });
      toast.success(`Uploaded ${res.filename}`);
    } catch (err) { toast.error(formatApiError(err)); }
    finally { setUploadingFor(null); }
  };

  const handleVideoFile = async (stid, file) => {
    if (!file) return;
    const videoExts = /\.(mp4|webm|mov|m4v|ogg)$/i;
    if (!videoExts.test(file.name)) {
      toast.error("Please choose an mp4/webm/mov/m4v/ogg video file");
      return;
    }
    if (file.size > 500 * 1024 * 1024) {
      toast.error("Video too large (max 500 MB). Consider hosting on YouTube/Drive instead.");
      return;
    }
    setUploadingVideoFor(stid);
    setVideoProgress({ ...videoProgress, [stid]: 0 });
    try {
      const res = await uploadFile(file, (pct) => setVideoProgress((prev) => ({ ...prev, [stid]: pct })));
      setLF(stid, { url: res.url });
      toast.success(`Uploaded ${res.filename}`);
    } catch (err) { toast.error(formatApiError(err)); }
    finally { setUploadingVideoFor(null); setVideoProgress((prev) => ({ ...prev, [stid]: 0 })); }
  };

  const addLesson = async (sid, stid) => {
    const f = lessonForm[stid] || {};
    if (!f.title?.trim()) return toast.error("Lesson title required");
    if (!f.url?.trim() && !(f.notes || []).length) return toast.error("Add either a video URL or at least one notes file");
    try {
      await api.post(
        `/courses/${id}/sections/${sid}/sub-topics/${stid}/lessons`,
        { title: f.title, url: f.url || "", duration: f.duration || "", notes: f.notes || [] }
      );
      setLessonForm({ ...lessonForm, [stid]: { title: "", url: "", duration: "", notes: [] } });
      toast.success("Lesson added");
      load();
    } catch (err) { toast.error(formatApiError(err)); }
  };

  const deleteLesson = async (lid) => {
    if (!window.confirm("Delete this lesson?")) return;
    try {
      await api.delete(`/courses/${id}/lessons/${lid}`);
      toast.success("Lesson deleted");
      load();
    } catch (err) { toast.error(formatApiError(err)); }
  };

  const reorderLesson = async (sid, stid, lessons, fromIdx, direction) => {
    const swapWith = direction === "up" ? fromIdx - 1 : fromIdx + 1;
    if (swapWith < 0 || swapWith >= lessons.length) return;
    const newOrder = [...lessons];
    [newOrder[fromIdx], newOrder[swapWith]] = [newOrder[swapWith], newOrder[fromIdx]];
    try {
      await api.put(
        `/courses/${id}/sections/${sid}/sub-topics/${stid}/lessons/reorder`,
        { lesson_ids: newOrder.map((l) => l.id) }
      );
      load();
    } catch (err) { toast.error(formatApiError(err)); }
  };

  const openLessonEditor = (sectionId, subTopicId, lesson) => {
    setEditingLesson({
      sectionId,
      subTopicId,
      id: lesson.id,
      title: lesson.title || "",
      url: lesson.url || "",
      duration: lesson.duration || "",
      notes: Array.isArray(lesson.notes) ? [...lesson.notes] : [],
    });
  };

  const saveLessonEdit = async () => {
    if (!editingLesson) return;
    const { id: lid, title, url, duration, notes } = editingLesson;
    if (!title.trim()) return toast.error("Lesson title required");
    if (!url.trim() && !(notes || []).length) return toast.error("Add either a video URL or at least one notes file");
    try {
      await api.put(`/courses/${id}/lessons/${lid}`, {
        title: title.trim(),
        url: url.trim(),
        duration: duration.trim(),
        notes: (notes || []).map((n) => ({ title: n.title, url: n.url })),
      });
      setEditingLesson(null);
      toast.success("Lesson updated");
      load();
    } catch (err) { toast.error(formatApiError(err)); }
  };

  const handleEditLessonNotesUpload = async (file) => {
    if (!file || !editingLesson) return;
    setLessonEditUploadingNotes(true);
    try {
      const res = await uploadFile(file);
      setEditingLesson((prev) => ({ ...prev, notes: [...(prev.notes || []), { title: res.filename, url: res.url }] }));
      toast.success(`Uploaded ${res.filename}`);
    } catch (err) { toast.error(formatApiError(err)); }
    finally { setLessonEditUploadingNotes(false); }
  };

  const handleEditLessonVideoUpload = async (file) => {
    if (!file || !editingLesson) return;
    const videoExts = /\.(mp4|webm|mov|m4v|ogg)$/i;
    if (!videoExts.test(file.name)) return toast.error("Please choose an mp4/webm/mov/m4v/ogg video file");
    if (file.size > 500 * 1024 * 1024) return toast.error("Video too large (max 500 MB).");
    setLessonEditUploadingVideo(true);
    setLessonEditVideoProgress(0);
    try {
      const res = await uploadFile(file, (pct) => setLessonEditVideoProgress(pct));
      setEditingLesson((prev) => ({ ...prev, url: res.url }));
      toast.success(`Uploaded ${res.filename}`);
    } catch (err) { toast.error(formatApiError(err)); }
    finally { setLessonEditUploadingVideo(false); setLessonEditVideoProgress(0); }
  };

  const addBatch = async (e) => {
    e.preventDefault();
    if (!batchForm.name.trim()) return;
    try {
      await api.post(`/courses/${id}/batches`, { ...batchForm, capacity: batchForm.capacity ? Number(batchForm.capacity) : null });
      setBatchForm({ name: "", start_date: "", schedule: "", capacity: "" });
      toast.success("Batch created");
      load();
    } catch (err) { toast.error(formatApiError(err)); }
  };

  const removeBatch = async (batchId) => {
    await api.delete(`/batches/${batchId}`);
    toast.success("Batch deleted");
    load();
  };

  const moveStudentBatch = async (studentId, newBatchId) => {
    try {
      await api.put(`/courses/${id}/students/${studentId}/batch`, { batch_id: newBatchId || null });
      toast.success(newBatchId ? "Student moved to new batch" : "Student switched to self-paced");
      load();
    } catch (err) { toast.error(formatApiError(err)); }
  };

  const openCourseEditor = () => {
    setEditingCourse({
      title: course.title || "",
      subject: course.subject || "Physics",
      description: course.description || "",
      duration: course.duration || "",
      price: course.price ?? 0,
      is_free: !!course.is_free,
      image_url: course.image_url || "",
    });
  };
  const saveCourseEdit = async () => {
    if (!editingCourse) return;
    const t = (editingCourse.title || "").trim();
    if (!t) return toast.error("Course title is required");
    if (!editingCourse.subject) return toast.error("Subject is required");
    const price = editingCourse.is_free ? 0 : Number(editingCourse.price);
    if (!editingCourse.is_free && (isNaN(price) || price < 0)) return toast.error("Price must be a non-negative number");
    try {
      await api.put(`/courses/${id}`, {
        title: t,
        subject: editingCourse.subject,
        description: editingCourse.description || "",
        duration: editingCourse.duration || "",
        price,
        is_free: !!editingCourse.is_free,
        image_url: editingCourse.image_url || "",
      });
      toast.success("Course updated");
      setEditingCourse(null);
      load();
    } catch (err) { toast.error(formatApiError(err)); }
  };

  const handleSyllabusFile = async (file) => {
    if (!file) return;
    const invalid = syllabusFileError(file);
    if (invalid) return toast.error(invalid);
    setSyllabusBusy(true);
    try {
      const res = await uploadFile(file);
      await api.put(`/courses/${id}/syllabus`, { url: res.url, filename: res.filename });
      toast.success(course.syllabus_url ? "Syllabus replaced" : "Syllabus uploaded");
      load();
    } catch (err) { toast.error(formatApiError(err)); }
    finally { setSyllabusBusy(false); }
  };

  const deleteSyllabus = async () => {
    if (!window.confirm("Delete the syllabus for this course? Students will no longer be able to view it.")) return;
    setSyllabusBusy(true);
    try {
      await api.delete(`/courses/${id}/syllabus`);
      toast.success("Syllabus deleted");
      load();
    } catch (err) { toast.error(formatApiError(err)); }
    finally { setSyllabusBusy(false); }
  };

  const deleteCourse = async () => {
    if (!course) return;
    const confirm1 = window.confirm(
      `Delete course "${course.title}"?\n\nThis will PERMANENTLY delete the course along with:\n  • All sections, sub-topics, lessons\n  • All tests, assignments, live classes, announcements\n  • All student enrollments and payments for this course\n  • All batches, submissions, certificates and comments\n\nThis cannot be undone.`
    );
    if (!confirm1) return;
    const typed = window.prompt(`To confirm, type the course title exactly:\n\n${course.title}`);
    if (typed !== course.title) {
      if (typed !== null) toast.error("Course title did not match — deletion cancelled");
      return;
    }
    try {
      const { data } = await api.delete(`/courses/${id}`);
      const c = data?.cascaded || {};
      toast.success(`Course deleted (${c.tests || 0} tests, ${c.assignments || 0} assignments, ${c.live_classes || 0} live classes cascaded)`);
      navigate("/app/courses");
    } catch (err) { toast.error(formatApiError(err)); }
  };

  return (
    <div className="space-y-8">
      <Link to="/app/courses" className="inline-flex items-center gap-1.5 text-sm text-zinc-500 hover:text-zinc-950" data-testid="back-to-courses">
        <ArrowLeft className="w-4 h-4" /> Back to courses
      </Link>
      <div className="flex flex-col md:flex-row gap-6 md:items-start justify-between">
        <div className="max-w-2xl">
          <span className="text-xs uppercase tracking-[0.2em] font-semibold text-blue-700">{course.subject}</span>
          <div className="flex items-center gap-3 mt-1 flex-wrap">
            <h1 className="font-heading text-3xl font-black tracking-tight" data-testid="course-detail-title">{course.title}</h1>
            {canEditCourse && (
              <>
                <button onClick={openCourseEditor} data-testid="course-edit-button" className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold border border-zinc-300 hover:bg-zinc-100">
                  <Edit2 className="w-3.5 h-3.5" /> Edit course
                </button>
                <button onClick={deleteCourse} data-testid="course-delete-button" className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold border border-red-300 text-red-600 hover:bg-red-50">
                  <Trash2 className="w-3.5 h-3.5" /> Delete course
                </button>
              </>
            )}
          </div>
          <p className="text-sm text-zinc-500 mt-3 leading-relaxed">{course.description}</p>
          <div className="flex gap-6 text-sm text-zinc-500 mt-4 flex-wrap">
            <span>Instructor: <span className="font-semibold text-zinc-950">{course.teacher_name}</span></span>
            {course.duration && <span>{course.duration}</span>}
            {user.role === "student" ? (
              course.syllabus_url ? (
                <a
                  href={course.syllabus_url.startsWith("/api/files/") ? fileUrl(course.syllabus_url) : course.syllabus_url}
                  target="_blank"
                  rel="noreferrer"
                  data-testid="course-detail-syllabus-link"
                  className="inline-flex items-center gap-1 font-semibold text-blue-700 hover:underline"
                >
                  <FileText className="w-4 h-4" /> Syllabus
                </a>
              ) : (
                <span data-testid="course-detail-syllabus-none" className="inline-flex items-center gap-1 text-zinc-400 italic" title="Syllabus not available yet">
                  <FileText className="w-4 h-4" /> Syllabus not available yet
                </span>
              )
            ) : (
              <span className="inline-flex items-center gap-1" data-testid="course-detail-enrolled-count"><Users className="w-4 h-4" />{course.enrolled_count} enrolled</span>
            )}
            {canEditCourse && (
              course.syllabus_url ? (
                <span className="inline-flex items-center gap-4 flex-wrap">
                  <a
                    href={course.syllabus_url.startsWith("/api/files/") ? fileUrl(course.syllabus_url) : course.syllabus_url}
                    target="_blank"
                    rel="noreferrer"
                    data-testid="syllabus-view-link"
                    title={course.syllabus_filename || "View syllabus"}
                    className="inline-flex items-center gap-1 font-semibold text-blue-700 hover:underline"
                  >
                    <FileText className="w-4 h-4" /> View Syllabus
                  </a>
                  <label className={`inline-flex items-center gap-1 font-semibold text-blue-700 cursor-pointer hover:underline ${syllabusBusy ? "opacity-50 pointer-events-none" : ""}`}>
                    <Upload className="w-4 h-4" /> {syllabusBusy ? "Uploading…" : "Replace Syllabus"}
                    <input type="file" data-testid="syllabus-replace-input" className="hidden" accept=".pdf,application/pdf" onChange={(e) => { handleSyllabusFile(e.target.files?.[0]); e.target.value = ""; }} />
                  </label>
                  <button onClick={deleteSyllabus} disabled={syllabusBusy} data-testid="syllabus-delete-button" className="inline-flex items-center gap-1 font-semibold text-red-600 hover:underline disabled:opacity-50">
                    <Trash2 className="w-4 h-4" /> Delete Syllabus
                  </button>
                </span>
              ) : (
                <label className={`inline-flex items-center gap-1 font-semibold text-blue-700 cursor-pointer hover:underline ${syllabusBusy ? "opacity-50 pointer-events-none" : ""}`} data-testid="syllabus-upload-label">
                  <Upload className="w-4 h-4" /> {syllabusBusy ? "Uploading syllabus…" : "Upload Syllabus"}
                  <input type="file" data-testid="syllabus-upload-input" className="hidden" accept=".pdf,application/pdf" onChange={(e) => { handleSyllabusFile(e.target.files?.[0]); e.target.value = ""; }} />
                </label>
              )
            )}
          </div>
        </div>
        {!isOwner && !course.enrolled && (
          <button onClick={() => setShowEnroll(true)} data-testid="course-detail-enroll-button" className="shrink-0 px-6 py-3 bg-blue-700 text-white font-semibold hover:bg-blue-900 transition-colors">
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

      {/* Cross-linked content */}
      <div className="grid md:grid-cols-3 gap-4" data-testid="course-linked-content">
        <LinkedList title="Live Classes" icon={Radio} testid="linked-live-classes" empty="No live classes scheduled." items={liveClasses}
          renderItem={(c) => (<div className="text-sm"><div className="font-semibold">{c.title}</div><div className="text-xs text-zinc-500 mt-0.5">{dayjs(c.start_time).format("D MMM, h:mm A")}{c.batch_name && ` · ${c.batch_name}`}</div></div>)}
          viewAllTo="/app/live" />
        <LinkedList title="Tests" icon={FileQuestion} testid="linked-tests" empty="No tests linked." items={tests}
          renderItem={(t) => (<div className="text-sm"><div className="font-semibold">{t.title}</div><div className="text-xs text-zinc-500 mt-0.5">{t.subject} · {t.questions?.length ?? 0} Qs · {t.duration_min} min</div></div>)}
          viewAllTo="/app/tests" />
        <LinkedList title="Assignments" icon={ClipboardList} testid="linked-assignments" empty="No assignments linked." items={assignments}
          renderItem={(a) => (<div className="text-sm"><div className="font-semibold">{a.title}</div><div className="text-xs text-zinc-500 mt-0.5">{a.subject}{a.due_date ? ` · Due ${dayjs(a.due_date).format("D MMM")}` : ""}</div></div>)}
          viewAllTo="/app/assignments" />
      </div>

      {isOwner && (
        <form onSubmit={addSection} className="flex gap-2">
          <input data-testid="new-section-input" value={sectionTitle} onChange={(e) => setSectionTitle(e.target.value)} placeholder="New section title (e.g. Thermodynamics)" className="flex-1 max-w-md border border-zinc-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-700" />
          <button data-testid="add-section-button" className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-semibold bg-blue-700 text-white hover:bg-blue-900">
            <Plus className="w-4 h-4" /> Add section
          </button>
        </form>
      )}

      <div className="space-y-4">
        <h2 className="font-heading text-xl font-bold">Curriculum</h2>
        {course.sections.length === 0 && <p className="text-sm text-zinc-500" data-testid="curriculum-empty">No content added yet.</p>}
        {course.sections.map((section, si) => {
          const sectionOpen = expandedSections[section.id] !== false; // default open
          const subTopics = [...section.sub_topics].sort((a, b) => (a.order ?? 0) - (b.order ?? 0));
          const isRenamingThis = renamingSection?.id === section.id;
          return (
            <div key={section.id} className="border border-zinc-200" data-testid={`section-${section.id}`}>
              <div className="w-full flex items-center gap-2 px-5 py-3 bg-zinc-50 border-b border-zinc-200 text-left">
                <button onClick={() => toggleSection(section.id)} data-testid={`section-toggle-${section.id}`} className="flex items-center gap-2 flex-1 min-w-0 text-left">
                  {sectionOpen ? <ChevronDown className="w-4 h-4 shrink-0" /> : <ChevronRight className="w-4 h-4 shrink-0" />}
                  {isRenamingThis ? (
                    <input
                      autoFocus
                      value={renamingSection.title}
                      onChange={(e) => setRenamingSection({ ...renamingSection, title: e.target.value })}
                      onKeyDown={(e) => { if (e.key === "Enter") renameSection(); if (e.key === "Escape") setRenamingSection(null); }}
                      onClick={(e) => e.stopPropagation()}
                      onBlur={renameSection}
                      data-testid={`section-rename-input-${section.id}`}
                      className="border-b border-blue-700 text-sm font-semibold bg-transparent focus:outline-none px-1 flex-1"
                    />
                  ) : (
                    <span className="font-semibold text-sm flex-1 truncate">{si + 1}. {section.title}</span>
                  )}
                  <span className="text-xs text-zinc-400 shrink-0">{subTopics.length} sub-topics · {subTopics.reduce((n, st) => n + st.lessons.length, 0)} lessons</span>
                </button>
                {isOwner && !isRenamingThis && (
                  <div className="flex items-center gap-0.5 shrink-0">
                    <button title="Rename section" onClick={(e) => { e.stopPropagation(); setRenamingSection({ id: section.id, title: section.title }); }} data-testid={`section-edit-${section.id}`} className="p-1.5 text-zinc-400 hover:text-zinc-950">
                      <Edit2 className="w-4 h-4" />
                    </button>
                    <button title="Delete section" onClick={(e) => { e.stopPropagation(); deleteSection(section.id); }} data-testid={`delete-section-${section.id}`} className="p-1.5 text-zinc-400 hover:text-red-600">
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                )}
              </div>
              {sectionOpen && (
                <>
                  {subTopics.map((st, sti) => {
                    const stOpen = expandedSubTopics[st.id] !== false; // default open
                    return (
                      <div key={st.id} className="border-b border-zinc-100 last:border-0" data-testid={`sub-topic-${st.id}`}>
                        <div className="flex items-center gap-2 px-5 py-2.5 bg-white border-b border-zinc-100">
                          <button onClick={() => toggleSubTopic(st.id)} className="flex items-center gap-1.5 flex-1 min-w-0 text-left" data-testid={`sub-topic-toggle-${st.id}`}>
                            {stOpen ? <ChevronDown className="w-3.5 h-3.5 text-zinc-400" /> : <ChevronRight className="w-3.5 h-3.5 text-zinc-400" />}
                            {renamingSubTopic?.id === st.id ? (
                              <input
                                autoFocus
                                value={renamingSubTopic.title}
                                onChange={(e) => setRenamingSubTopic({ ...renamingSubTopic, title: e.target.value })}
                                onKeyDown={(e) => { if (e.key === "Enter") renameSubTopic(); if (e.key === "Escape") setRenamingSubTopic(null); }}
                                onClick={(e) => e.stopPropagation()}
                                onBlur={renameSubTopic}
                                data-testid={`sub-topic-rename-input-${st.id}`}
                                className="border-b border-blue-700 text-sm font-medium bg-transparent focus:outline-none px-1"
                              />
                            ) : (
                              <span className="text-sm font-medium truncate">{st.title}</span>
                            )}
                            <span className="text-xs text-zinc-400">· {st.lessons.length} lessons</span>
                          </button>
                          {isOwner && (
                            <div className="flex items-center gap-0.5 shrink-0">
                              <button title="Move up" disabled={sti === 0} onClick={() => reorderSubTopic(section.id, subTopics, sti, "up")} data-testid={`sub-topic-up-${st.id}`} className="p-1 text-zinc-400 hover:text-zinc-950 disabled:opacity-20"><GripVertical className="w-3.5 h-3.5 -rotate-90" /></button>
                              <button title="Move down" disabled={sti === subTopics.length - 1} onClick={() => reorderSubTopic(section.id, subTopics, sti, "down")} data-testid={`sub-topic-down-${st.id}`} className="p-1 text-zinc-400 hover:text-zinc-950 disabled:opacity-20"><GripVertical className="w-3.5 h-3.5 rotate-90" /></button>
                              <button title="Rename" onClick={() => setRenamingSubTopic({ sectionId: section.id, id: st.id, title: st.title })} data-testid={`sub-topic-edit-${st.id}`} className="p-1 text-zinc-400 hover:text-zinc-950"><Edit2 className="w-3.5 h-3.5" /></button>
                              <button title={st.comments_enabled ? "Disable comments" : "Enable comments"} onClick={() => toggleSubTopicComments(section.id, st.id, st.comments_enabled)} data-testid={`sub-topic-comments-toggle-${st.id}`} className={`p-1 hover:text-zinc-950 ${st.comments_enabled ? "text-blue-700" : "text-zinc-400"}`}>
                                {st.comments_enabled ? <MessageSquare className="w-3.5 h-3.5" /> : <MessageSquareOff className="w-3.5 h-3.5" />}
                              </button>
                              <button title="Delete" onClick={() => deleteSubTopic(section.id, st.id)} data-testid={`sub-topic-delete-${st.id}`} className="p-1 text-zinc-400 hover:text-red-600"><Trash2 className="w-3.5 h-3.5" /></button>
                            </div>
                          )}
                        </div>
                        {stOpen && (
                          <>
                            {st.lessons.length === 0 && <p className="px-8 py-3 text-xs text-zinc-400">No lessons yet.</p>}
                            {st.lessons.map((lesson, li) => {
                              const done = course.completed_lessons?.includes(lesson.id);
                              const hasVideo = Boolean(lesson.url);
                              const hasNotes = (lesson.notes || []).length > 0;
                              return (
                                <div key={lesson.id} className="pl-10 pr-5 py-2.5 border-b border-zinc-50 last:border-0 flex items-center gap-3" data-testid={`lesson-${lesson.id}`}>
                                  {hasVideo ? <PlayCircle className="w-4 h-4 text-blue-700 shrink-0" /> : <FileText className="w-4 h-4 text-red-600 shrink-0" />}
                                  <div className="flex-1 min-w-0">
                                    <Link to={`/app/courses/${id}/lessons/${lesson.id}`} data-testid={`open-lesson-${lesson.id}`} className="text-sm font-medium hover:text-blue-700 hover:underline">
                                      {lesson.title}
                                    </Link>
                                    <span className="text-xs text-zinc-400 ml-2">
                                      {lesson.duration}
                                      {hasVideo && hasNotes && " · Video + Notes"}
                                      {!hasVideo && hasNotes && ` · ${lesson.notes.length} note${lesson.notes.length > 1 ? "s" : ""}`}
                                    </span>
                                  </div>
                                  {isOwner && (
                                    <div className="flex items-center gap-0.5 shrink-0">
                                      <button title="Move up" disabled={li === 0} onClick={() => reorderLesson(section.id, st.id, st.lessons, li, "up")} data-testid={`lesson-up-${lesson.id}`} className="p-1 text-zinc-400 hover:text-zinc-950 disabled:opacity-20"><GripVertical className="w-3.5 h-3.5 -rotate-90" /></button>
                                      <button title="Move down" disabled={li === st.lessons.length - 1} onClick={() => reorderLesson(section.id, st.id, st.lessons, li, "down")} data-testid={`lesson-down-${lesson.id}`} className="p-1 text-zinc-400 hover:text-zinc-950 disabled:opacity-20"><GripVertical className="w-3.5 h-3.5 rotate-90" /></button>
                                      <button title="Edit lesson" onClick={() => openLessonEditor(section.id, st.id, lesson)} data-testid={`edit-lesson-${lesson.id}`} className="p-1 text-zinc-400 hover:text-zinc-950"><Edit2 className="w-3.5 h-3.5" /></button>
                                      <button title="Delete lesson" onClick={() => deleteLesson(lesson.id)} data-testid={`delete-lesson-${lesson.id}`} className="p-1 text-zinc-400 hover:text-red-600"><Trash2 className="w-3.5 h-3.5" /></button>
                                    </div>
                                  )}
                                  {!isOwner && course.enrolled && (
                                    <button onClick={() => toggleComplete(lesson.id)} data-testid={`complete-lesson-${lesson.id}`} title={done ? "Completed" : "Mark complete"}>
                                      {done ? <CheckCircle2 className="w-5 h-5 text-green-600" /> : <Circle className="w-5 h-5 text-zinc-300 hover:text-blue-700" />}
                                    </button>
                                  )}
                                </div>
                              );
                            })}
                            {isOwner && (
                              <div className="pl-10 pr-5 py-3 bg-zinc-50/60 space-y-2">
                                <div className="grid sm:grid-cols-6 gap-2 items-center">
                                  <input data-testid={`lesson-title-input-${st.id}`} value={lessonForm[st.id]?.title || ""} onChange={(e) => setLF(st.id, { title: e.target.value })} placeholder="Lesson title" className="sm:col-span-2 border border-zinc-300 px-2.5 py-1.5 text-sm" />
                                  <input data-testid={`lesson-url-input-${st.id}`} value={lessonForm[st.id]?.url || ""} onChange={(e) => setLF(st.id, { url: e.target.value })} placeholder="Video URL (YouTube/Drive) or uploaded file" className="sm:col-span-2 border border-zinc-300 px-2.5 py-1.5 text-sm" />
                                  <input data-testid={`lesson-duration-input-${st.id}`} value={lessonForm[st.id]?.duration || ""} onChange={(e) => setLF(st.id, { duration: e.target.value })} placeholder="Duration" className="border border-zinc-300 px-2.5 py-1.5 text-sm" />
                                  <button type="button" onClick={() => addLesson(section.id, st.id)} data-testid={`add-lesson-button-${st.id}`} className="px-3 py-1.5 text-sm font-semibold border border-zinc-300 bg-white hover:bg-zinc-100">Add lesson</button>
                                </div>
                                {(lessonForm[st.id]?.notes || []).length > 0 && (
                                  <div className="flex flex-wrap gap-2">
                                    {(lessonForm[st.id]?.notes || []).map((n, ni) => (
                                      <span key={ni} className="inline-flex items-center gap-1 text-xs bg-white border border-zinc-200 px-2 py-1">
                                        <FileText className="w-3 h-3 text-red-600" />{n.title}
                                        <button type="button" onClick={() => setLF(st.id, { notes: lessonForm[st.id].notes.filter((_, i) => i !== ni) })} className="text-zinc-400 hover:text-red-600 ml-1">×</button>
                                      </span>
                                    ))}
                                  </div>
                                )}
                                <div className="flex flex-wrap gap-4">
                                  <label className="inline-flex items-center gap-2 text-xs font-semibold text-blue-700 cursor-pointer hover:underline">
                                    <Upload className="w-3.5 h-3.5" />
                                    {uploadingVideoFor === st.id
                                      ? `Uploading video ${videoProgress[st.id] ?? 0}%…`
                                      : "Upload video file (mp4/webm/mov, max 500 MB)"}
                                    <input type="file" data-testid={`lesson-video-input-${st.id}`} className="hidden" accept="video/mp4,video/webm,video/quicktime,.mp4,.webm,.mov,.m4v,.ogg" onChange={(e) => handleVideoFile(st.id, e.target.files?.[0])} />
                                  </label>
                                  <label className="inline-flex items-center gap-2 text-xs font-semibold text-blue-700 cursor-pointer hover:underline">
                                    <Upload className="w-3.5 h-3.5" />
                                    {uploadingFor === st.id ? "Uploading notes…" : "Attach notes / PDF (max 25 MB)"}
                                    <input type="file" data-testid={`lesson-notes-input-${st.id}`} className="hidden" accept=".pdf,.doc,.docx,.png,.jpg,.jpeg,.webp,.txt,.ppt,.pptx,.xlsx,.zip,.csv" onChange={(e) => handleNotesFile(st.id, e.target.files?.[0])} />
                                  </label>
                                </div>
                              </div>
                            )}
                          </>
                        )}
                      </div>
                    );
                  })}
                  {isOwner && (
                    <div className="flex items-center gap-2 px-5 py-3 bg-zinc-50 border-t border-zinc-100">
                      <input data-testid={`new-sub-topic-input-${section.id}`} value={subTopicForm[section.id] || ""} onChange={(e) => setSubTopicForm({ ...subTopicForm, [section.id]: e.target.value })} onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addSubTopic(section.id); }}} placeholder="Add sub topic…" className="flex-1 max-w-xs border border-zinc-300 px-2.5 py-1.5 text-sm" />
                      <button type="button" onClick={() => addSubTopic(section.id)} data-testid={`add-sub-topic-button-${section.id}`} className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-semibold border border-zinc-300 hover:bg-zinc-100">
                        <Plus className="w-3.5 h-3.5" /> Add sub topic
                      </button>
                    </div>
                  )}
                </>
              )}
            </div>
          );
        })}
      </div>

      {isOwner && (
        <div className="space-y-3">
          <h2 className="font-heading text-xl font-bold">Enrolled Students ({students.length})</h2>
          <div className="border border-zinc-200 overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-zinc-50 text-left text-xs uppercase tracking-[0.1em] text-zinc-500">
                <tr>
                  <th className="px-5 py-3 font-semibold">Name</th>
                  <th className="px-5 py-3 font-semibold">Email</th>
                  <th className="px-5 py-3 font-semibold">Enrolled</th>
                  <th className="px-5 py-3 font-semibold">Batch</th>
                  <th className="px-5 py-3 font-semibold">Lessons done</th>
                </tr>
              </thead>
              <tbody>
                {students.map((s) => (
                  <tr key={s.id} className="border-t border-zinc-100" data-testid={`enrolled-student-${s.id}`}>
                    <td className="px-5 py-3 font-medium">{s.name}</td>
                    <td className="px-5 py-3 text-zinc-500">{s.email}</td>
                    <td className="px-5 py-3 text-zinc-500">{s.enrolled_at ? dayjs(s.enrolled_at).format("D MMM YYYY") : "—"}</td>
                    <td className="px-5 py-3 text-zinc-500">
                      <select
                        value={s.batch_id || ""}
                        onChange={(e) => moveStudentBatch(s.id, e.target.value)}
                        data-testid={`move-student-batch-${s.id}`}
                        className="border border-zinc-300 px-2 py-1 text-xs bg-white"
                      >
                        <option value="">Self-paced</option>
                        {batches.map((b) => (
                          <option key={b.id} value={b.id}>{b.name}</option>
                        ))}
                      </select>
                    </td>
                    <td className="px-5 py-3 text-zinc-500">{s.completed_lessons}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {students.length === 0 && <p className="px-5 py-6 text-sm text-zinc-500">No students enrolled yet.</p>}
          </div>
        </div>
      )}

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
                      <td className="px-5 py-3 text-zinc-500">{b.start_date ? dayjs(b.start_date).format("D MMM YYYY") : "—"}</td>
                      <td className="px-5 py-3 text-zinc-500">{b.enrolled_count}{b.capacity ? ` / ${b.capacity}` : ""}</td>
                      <td className="px-5 py-3 text-right">
                        <button onClick={() => removeBatch(b.id)} data-testid={`delete-batch-${b.id}`} className="p-1.5 text-zinc-400 hover:text-red-600"><Trash2 className="w-4 h-4" /></button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {showEnroll && (
        <EnrollModal course={course} batches={batches} onClose={() => setShowEnroll(false)} onDone={() => { setShowEnroll(false); load(); }} />
      )}

      {editingCourse && (
        <div className="fixed inset-0 z-50 bg-zinc-950/60 flex items-center justify-center p-4" data-testid="course-edit-modal" onClick={() => setEditingCourse(null)}>
          <div className="bg-white w-full max-w-2xl border border-zinc-200 shadow-xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-200">
              <h3 className="font-heading font-bold text-lg">Edit course</h3>
              <button onClick={() => setEditingCourse(null)} data-testid="course-edit-close" className="text-zinc-400 hover:text-zinc-950 text-2xl leading-none">×</button>
            </div>
            <div className="px-6 py-5 space-y-4 max-h-[70vh] overflow-y-auto">
              <div>
                <label className="text-xs uppercase tracking-[0.15em] font-semibold text-zinc-500">Course name</label>
                <input data-testid="course-edit-title" value={editingCourse.title} onChange={(e) => setEditingCourse({ ...editingCourse, title: e.target.value })} maxLength={200} className="mt-1.5 w-full border border-zinc-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-700" />
              </div>
              <div className="grid sm:grid-cols-2 gap-3">
                <div>
                  <label className="text-xs uppercase tracking-[0.15em] font-semibold text-zinc-500">Subject</label>
                  <select data-testid="course-edit-subject" value={editingCourse.subject} onChange={(e) => setEditingCourse({ ...editingCourse, subject: e.target.value })} className="mt-1.5 w-full border border-zinc-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-700 bg-white">
                    {["Physics", "Chemistry", "Mathematics", "Biotechnology"].map((s) => <option key={s}>{s}</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-xs uppercase tracking-[0.15em] font-semibold text-zinc-500">Duration</label>
                  <input data-testid="course-edit-duration" value={editingCourse.duration} onChange={(e) => setEditingCourse({ ...editingCourse, duration: e.target.value })} placeholder="6 months" className="mt-1.5 w-full border border-zinc-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-700" />
                </div>
              </div>
              <div>
                <label className="text-xs uppercase tracking-[0.15em] font-semibold text-zinc-500">Description</label>
                <textarea data-testid="course-edit-description" value={editingCourse.description} onChange={(e) => setEditingCourse({ ...editingCourse, description: e.target.value })} rows={4} maxLength={5000} className="mt-1.5 w-full border border-zinc-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-700 resize-none" />
              </div>
              <div>
                <label className="text-xs uppercase tracking-[0.15em] font-semibold text-zinc-500">Cover image URL (optional)</label>
                <input data-testid="course-edit-image" value={editingCourse.image_url} onChange={(e) => setEditingCourse({ ...editingCourse, image_url: e.target.value })} placeholder="https://…" className="mt-1.5 w-full border border-zinc-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-700" />
              </div>
              <div className="grid sm:grid-cols-[1fr_auto] gap-3 items-end">
                <div>
                  <label className="text-xs uppercase tracking-[0.15em] font-semibold text-zinc-500">Price (₹)</label>
                  <input data-testid="course-edit-price" type="number" min={0} value={editingCourse.is_free ? 0 : editingCourse.price} disabled={editingCourse.is_free} onChange={(e) => setEditingCourse({ ...editingCourse, price: e.target.value })} className="mt-1.5 w-full border border-zinc-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-700 disabled:bg-zinc-100" />
                </div>
                <label className="inline-flex items-center gap-2 pb-2 text-sm">
                  <input data-testid="course-edit-is-free" type="checkbox" checked={editingCourse.is_free} onChange={(e) => setEditingCourse({ ...editingCourse, is_free: e.target.checked })} />
                  Free course
                </label>
              </div>
            </div>
            <div className="flex items-center justify-end gap-2 px-6 py-4 border-t border-zinc-200 bg-zinc-50">
              <button onClick={() => setEditingCourse(null)} data-testid="course-edit-cancel" className="px-4 py-2 text-sm font-semibold border border-zinc-300 hover:bg-zinc-100">Cancel</button>
              <button onClick={saveCourseEdit} data-testid="course-edit-save" className="px-4 py-2 text-sm font-semibold bg-blue-700 text-white hover:bg-blue-900">Save changes</button>
            </div>
          </div>
        </div>
      )}

      {editingLesson && (
        <div className="fixed inset-0 z-50 bg-zinc-950/60 flex items-center justify-center p-4" data-testid="lesson-edit-modal" onClick={() => setEditingLesson(null)}>
          <div className="bg-white w-full max-w-2xl border border-zinc-200 shadow-xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-200">
              <h3 className="font-heading font-bold text-lg">Edit lesson</h3>
              <button onClick={() => setEditingLesson(null)} data-testid="lesson-edit-close" className="text-zinc-400 hover:text-zinc-950">×</button>
            </div>
            <div className="px-6 py-5 space-y-4 max-h-[70vh] overflow-y-auto">
              <div>
                <label className="text-xs uppercase tracking-[0.15em] font-semibold text-zinc-500">Lesson title</label>
                <input
                  data-testid="lesson-edit-title"
                  value={editingLesson.title}
                  onChange={(e) => setEditingLesson({ ...editingLesson, title: e.target.value })}
                  className="mt-1.5 w-full border border-zinc-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-700"
                />
              </div>
              <div className="grid sm:grid-cols-[1fr_140px] gap-3">
                <div>
                  <label className="text-xs uppercase tracking-[0.15em] font-semibold text-zinc-500">Video URL</label>
                  <input
                    data-testid="lesson-edit-url"
                    value={editingLesson.url}
                    onChange={(e) => setEditingLesson({ ...editingLesson, url: e.target.value })}
                    placeholder="YouTube / Drive / uploaded video URL"
                    className="mt-1.5 w-full border border-zinc-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-700"
                  />
                </div>
                <div>
                  <label className="text-xs uppercase tracking-[0.15em] font-semibold text-zinc-500">Duration</label>
                  <input
                    data-testid="lesson-edit-duration"
                    value={editingLesson.duration}
                    onChange={(e) => setEditingLesson({ ...editingLesson, duration: e.target.value })}
                    placeholder="45 min"
                    className="mt-1.5 w-full border border-zinc-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-700"
                  />
                </div>
              </div>
              <div className="flex flex-wrap gap-4">
                <label className="inline-flex items-center gap-2 text-xs font-semibold text-blue-700 cursor-pointer hover:underline">
                  <Upload className="w-3.5 h-3.5" />
                  {lessonEditUploadingVideo ? `Uploading video ${lessonEditVideoProgress}%…` : "Replace video (mp4/webm/mov, max 500 MB)"}
                  <input type="file" data-testid="lesson-edit-video-input" className="hidden" accept="video/mp4,video/webm,video/quicktime,.mp4,.webm,.mov,.m4v,.ogg" onChange={(e) => handleEditLessonVideoUpload(e.target.files?.[0])} />
                </label>
                <label className="inline-flex items-center gap-2 text-xs font-semibold text-blue-700 cursor-pointer hover:underline">
                  <Upload className="w-3.5 h-3.5" />
                  {lessonEditUploadingNotes ? "Uploading notes…" : "Attach notes / PDF (max 25 MB)"}
                  <input type="file" data-testid="lesson-edit-notes-input" className="hidden" accept=".pdf,.doc,.docx,.png,.jpg,.jpeg,.webp,.txt,.ppt,.pptx,.xlsx,.zip,.csv" onChange={(e) => handleEditLessonNotesUpload(e.target.files?.[0])} />
                </label>
              </div>
              <div>
                <label className="text-xs uppercase tracking-[0.15em] font-semibold text-zinc-500">Notes attached</label>
                {(editingLesson.notes || []).length === 0 ? (
                  <p className="mt-2 text-xs text-zinc-400">No notes attached.</p>
                ) : (
                  <ul className="mt-2 space-y-1.5" data-testid="lesson-edit-notes-list">
                    {editingLesson.notes.map((n, ni) => (
                      <li key={ni} className="flex items-center gap-2 border border-zinc-200 px-3 py-2 text-sm">
                        <FileText className="w-3.5 h-3.5 text-red-600" />
                        <input
                          value={n.title}
                          onChange={(e) => {
                            const notes = [...editingLesson.notes];
                            notes[ni] = { ...notes[ni], title: e.target.value };
                            setEditingLesson({ ...editingLesson, notes });
                          }}
                          data-testid={`lesson-edit-note-title-${ni}`}
                          className="flex-1 text-sm border-none focus:outline-none bg-transparent"
                        />
                        <a href={fileUrl(n.url)} target="_blank" rel="noreferrer" className="text-xs text-blue-700 hover:underline">Open</a>
                        <button
                          type="button"
                          onClick={() => setEditingLesson({ ...editingLesson, notes: editingLesson.notes.filter((_, i) => i !== ni) })}
                          data-testid={`lesson-edit-note-remove-${ni}`}
                          className="text-zinc-400 hover:text-red-600 text-xs"
                        >×</button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
            <div className="flex items-center justify-end gap-2 px-6 py-4 border-t border-zinc-200 bg-zinc-50">
              <button onClick={() => setEditingLesson(null)} data-testid="lesson-edit-cancel" className="px-4 py-2 text-sm font-semibold border border-zinc-300 hover:bg-zinc-100">Cancel</button>
              <button onClick={saveLessonEdit} data-testid="lesson-edit-save" className="px-4 py-2 text-sm font-semibold bg-blue-700 text-white hover:bg-blue-900">Save changes</button>
            </div>
          </div>
        </div>
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
        <Link to={viewAllTo} className="block text-center px-4 py-2 border-t border-zinc-200 text-xs font-semibold text-blue-700 hover:bg-zinc-50">View all →</Link>
      )}
    </div>
  );
}

// re-export for legacy fileUrl usage
export { fileUrl };
