import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { api, formatApiError } from "@/lib/api";
import EnrollModal from "@/components/EnrollModal";
import { toast } from "sonner";
import { Plus, Users, Clock } from "lucide-react";

function CourseCard({ course, footer }) {
  return (
    <div className="border border-zinc-200 bg-white flex flex-col hover:border-zinc-300 hover:shadow-sm transition-all" data-testid={`course-card-${course.id}`}>
      {course.thumbnail && <img src={course.thumbnail} alt={course.title} className="h-36 w-full object-cover" />}
      <div className="p-5 flex-1 flex flex-col">
        <span className="text-xs uppercase tracking-[0.15em] font-semibold text-blue-700">{course.subject}</span>
        <h3 className="font-heading font-bold mt-1.5 leading-snug">{course.title}</h3>
        <p className="text-xs text-zinc-500 mt-2 line-clamp-2 flex-1">{course.description}</p>
        <div className="flex items-center gap-4 text-xs text-zinc-500 mt-3">
          <span className="inline-flex items-center gap-1"><Clock className="w-3.5 h-3.5" />{course.duration}</span>
          {course.is_free || !course.price ? (
            <span className="font-bold text-green-700 text-xs uppercase tracking-[0.15em]" data-testid={`course-free-badge-${course.id}`}>Free</span>
          ) : (
            <span className="font-semibold text-zinc-950">₹{course.price}</span>
          )}
        </div>
        <div className="mt-4">{footer}</div>
      </div>
    </div>
  );
}

export default function CoursesPage() {
  const { user } = useAuth();
  const [tab, setTab] = useState("all");
  const [courses, setCourses] = useState([]);
  const [myCourses, setMyCourses] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [payCourse, setPayCourse] = useState(null);
  const [form, setForm] = useState({ title: "", subject: "Physics", description: "", price: 0, is_free: false, duration: "", thumbnail: "" });

  const isTeacher = user.role !== "student";

  const load = () => {
    if (isTeacher) {
      api.get("/teacher/courses").then((r) => setCourses(r.data));
    } else {
      api.get("/courses").then((r) => setCourses(r.data));
      api.get("/student/enrollments").then((r) => setMyCourses(r.data));
    }
  };
  useEffect(load, []);

  const createCourse = async (e) => {
    e.preventDefault();
    try {
      await api.post("/courses", { ...form, price: form.is_free ? 0 : Number(form.price), published: true });
      toast.success("Course created");
      setShowForm(false);
      setForm({ title: "", subject: "Physics", description: "", price: 0, is_free: false, duration: "", thumbnail: "" });
      load();
    } catch (err) {
      toast.error(formatApiError(err));
    }
  };

  const enrolledIds = new Set(myCourses.map((c) => c.id));

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between flex-wrap gap-4">
        <h1 className="font-heading text-3xl font-black tracking-tight">Courses</h1>
        {isTeacher && (
          <button onClick={() => setShowForm(!showForm)} data-testid="new-course-button" className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-semibold bg-blue-700 text-white hover:bg-blue-900 transition-colors">
            <Plus className="w-4 h-4" /> New course
          </button>
        )}
      </div>

      {isTeacher && showForm && (
        <form onSubmit={createCourse} className="border border-zinc-200 p-6 grid sm:grid-cols-2 gap-4" data-testid="new-course-form">
          <div className="sm:col-span-2">
            <label className="text-xs uppercase tracking-[0.15em] font-semibold text-zinc-500">Title</label>
            <input data-testid="course-title-input" required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} className="mt-1 w-full border border-zinc-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-700" />
          </div>
          <div>
            <label className="text-xs uppercase tracking-[0.15em] font-semibold text-zinc-500">Subject</label>
            <select data-testid="course-subject-select" value={form.subject} onChange={(e) => setForm({ ...form, subject: e.target.value })} className="mt-1 w-full border border-zinc-300 px-3 py-2 text-sm bg-white">
              {["Physics", "Chemistry", "Mathematics", "Biotechnology", "Economics", "Geology"].map((s) => <option key={s}>{s}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs uppercase tracking-[0.15em] font-semibold text-zinc-500">Duration</label>
            <input data-testid="course-duration-input" value={form.duration} onChange={(e) => setForm({ ...form, duration: e.target.value })} placeholder="6 months" className="mt-1 w-full border border-zinc-300 px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="text-xs uppercase tracking-[0.15em] font-semibold text-zinc-500">Price (₹)</label>
            <input data-testid="course-price-input" type="number" min="0" disabled={form.is_free} value={form.is_free ? 0 : form.price} onChange={(e) => setForm({ ...form, price: e.target.value })} className="mt-1 w-full border border-zinc-300 px-3 py-2 text-sm disabled:opacity-50" />
            <label className="mt-2 flex items-center gap-2 text-xs cursor-pointer">
              <input type="checkbox" data-testid="course-is-free-checkbox" checked={form.is_free} onChange={(e) => setForm({ ...form, is_free: e.target.checked, price: e.target.checked ? 0 : form.price })} className="accent-blue-700" />
              <span className="font-semibold text-green-700">This is a Free course</span>
            </label>
          </div>
          <div>
            <label className="text-xs uppercase tracking-[0.15em] font-semibold text-zinc-500">Thumbnail URL (optional)</label>
            <input data-testid="course-thumbnail-input" value={form.thumbnail} onChange={(e) => setForm({ ...form, thumbnail: e.target.value })} className="mt-1 w-full border border-zinc-300 px-3 py-2 text-sm" />
          </div>
          <div className="sm:col-span-2">
            <label className="text-xs uppercase tracking-[0.15em] font-semibold text-zinc-500">Description</label>
            <textarea data-testid="course-description-input" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} rows={3} className="mt-1 w-full border border-zinc-300 px-3 py-2 text-sm" />
          </div>
          <div className="sm:col-span-2 flex gap-2">
            <button data-testid="course-submit-button" className="px-5 py-2 text-sm font-semibold bg-blue-700 text-white hover:bg-blue-900">Create course</button>
            <button type="button" onClick={() => setShowForm(false)} className="px-5 py-2 text-sm font-semibold border border-zinc-300 hover:bg-zinc-100">Cancel</button>
          </div>
        </form>
      )}

      {!isTeacher && (
        <div className="flex gap-px bg-zinc-200 border border-zinc-200 w-fit">
          {[["all", "All Courses"], ["my", "My Courses"]].map(([k, label]) => (
            <button key={k} data-testid={`courses-tab-${k}`} onClick={() => setTab(k)} className={`px-5 py-2 text-sm font-semibold transition-colors ${tab === k ? "bg-blue-700 text-white" : "bg-white text-zinc-500 hover:bg-zinc-50"}`}>
              {label}
            </button>
          ))}
        </div>
      )}

      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {(isTeacher ? courses : tab === "all" ? courses : myCourses).map((course) => (
          <CourseCard
            key={course.id}
            course={course}
            footer={
              isTeacher ? (
                <div className="flex items-center justify-between">
                  <span className="text-xs text-zinc-500 inline-flex items-center gap-1"><Users className="w-3.5 h-3.5" />{course.enrolled_count} enrolled</span>
                  <Link to={`/app/courses/${course.id}`} data-testid={`manage-course-${course.id}`} className="text-sm font-semibold text-blue-700 hover:underline">Manage →</Link>
                </div>
              ) : tab === "my" ? (
                <div>
                  <div className="flex justify-between text-xs text-zinc-500 mb-1.5">
                    <span>Progress</span>
                    <span className="font-semibold text-zinc-950">{course.progress}%</span>
                  </div>
                  <div className="h-1.5 bg-zinc-100"><div className="h-full bg-blue-700" style={{ width: `${course.progress}%` }} /></div>
                  {course.progress === 100 ? (
                    <div className="mt-3 grid grid-cols-2 gap-2">
                      <Link to={`/app/courses/${course.id}`} className="block text-center py-2 text-sm font-semibold border border-zinc-300 hover:bg-zinc-100 transition-colors">Revisit</Link>
                      <Link to={`/certificate/${course.id}`} data-testid={`view-certificate-${course.id}`} className="block text-center py-2 text-sm font-semibold bg-zinc-950 text-white hover:bg-zinc-800 transition-colors">Certificate</Link>
                    </div>
                  ) : (
                    <Link to={`/app/courses/${course.id}`} data-testid={`continue-course-${course.id}`} className="mt-3 block text-center py-2 text-sm font-semibold bg-blue-700 text-white hover:bg-blue-900 transition-colors">Continue learning</Link>
                  )}
                </div>
              ) : enrolledIds.has(course.id) ? (
                <Link to={`/app/courses/${course.id}`} className="block text-center py-2 text-sm font-semibold border border-zinc-300 hover:bg-zinc-100 transition-colors">Enrolled — View course</Link>
              ) : (
                <button onClick={() => setPayCourse(course)} data-testid={`enroll-button-${course.id}`} className="w-full py-2 text-sm font-semibold bg-blue-700 text-white hover:bg-blue-900 transition-colors">Enroll now</button>
              )
            }
          />
        ))}
      </div>
      {(isTeacher ? courses : tab === "all" ? courses : myCourses).length === 0 && (
        <p className="text-sm text-zinc-500 py-8" data-testid="courses-empty-state">
          {isTeacher ? "You haven't created any courses yet." : tab === "my" ? "You are not enrolled in any course yet. Browse All Courses to start." : "No courses available yet."}
        </p>
      )}
      {payCourse && (
        <EnrollModal
          course={payCourse}
          onClose={() => setPayCourse(null)}
          onSuccess={() => { setPayCourse(null); load(); }}
        />
      )}
    </div>
  );
}
