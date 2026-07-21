// Single-lesson viewer ("/app/courses/:courseId/lessons/:lessonId") —
// video (via LessonVideoPlayer) and/or downloadable notes, prev/next
// navigation within the course, and a discussion thread (CommentsThread).
// Auto-marks the lesson complete for students once 90% of the video plays.
import { useEffect, useState, useCallback } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { api, formatApiError, fileUrl } from "@/lib/api";
import { ArrowLeft, ArrowRight, FileText } from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/context/AuthContext";
import LessonVideoPlayer from "@/components/LessonVideoPlayer";
import CommentsThread from "@/components/CommentsThread";

export default function LessonPage() {
  const { courseId, lessonId } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.get(`/courses/${courseId}/lessons/${lessonId}`).then((r) => {
      setData(r.data);
      setLoading(false);
    }).catch((err) => {
      toast.error(formatApiError(err));
      navigate(`/app/courses/${courseId}`);
    });
  }, [courseId, lessonId, navigate]);

  const markComplete = useCallback(async () => {
    if (user.role !== "student") return;
    try {
      await api.post(`/courses/${courseId}/lessons/${lessonId}/complete`);
      toast.success("Lesson marked complete");
    } catch (err) {
      toast.error(formatApiError(err));
    }
  }, [courseId, lessonId, user.role]);

  if (loading || !data) return <p className="text-sm text-zinc-500" data-testid="lesson-loading">Loading lesson…</p>;

  const { lesson, section_title, sub_topic_title, course_title, prev_lesson_id, next_lesson_id } = data;
  const notes = lesson.notes || [];

  return (
    <div className="max-w-4xl mx-auto space-y-6" data-testid="lesson-page">
      <Link to={`/app/courses/${courseId}`} className="inline-flex items-center gap-1.5 text-sm text-zinc-500 hover:text-zinc-950" data-testid="lesson-back-to-course">
        <ArrowLeft className="w-4 h-4" /> Back to {course_title}
      </Link>

      <div>
        <p className="text-xs uppercase tracking-[0.2em] font-semibold text-zinc-400">{section_title} · {sub_topic_title}</p>
        <h1 className="font-heading text-3xl font-black tracking-tight mt-1" data-testid="lesson-title">{lesson.title}</h1>
        {lesson.duration && <p className="text-xs text-zinc-500 mt-1">{lesson.duration}</p>}
      </div>

      {lesson.url ? (
        <LessonVideoPlayer
          url={lesson.url}
          canTrackProgress={user.role === "student"}
          onProgress90={markComplete}
        />
      ) : (
        <div className="border border-dashed border-zinc-300 p-8 text-center text-sm text-zinc-500" data-testid="lesson-no-video">
          This lesson has no video. Review the notes below.
        </div>
      )}

      {notes.length > 0 && (
        <div className="border border-zinc-200" data-testid="lesson-notes">
          <div className="px-4 py-2.5 bg-zinc-50 border-b border-zinc-200 font-semibold text-xs uppercase tracking-[0.1em]">Notes & Reference Material ({notes.length})</div>
          <ul className="divide-y divide-zinc-100">
            {notes.map((n, i) => (
              <li key={i} className="px-4 py-3 flex items-center gap-3">
                <FileText className="w-4 h-4 text-red-600 shrink-0" />
                <a href={fileUrl(n.url) || n.url} target="_blank" rel="noreferrer" data-testid={`lesson-note-${i}`} className="text-sm font-medium text-blue-700 hover:underline flex-1">
                  {n.title}
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Phase 4: reusable Comments component */}
      <CommentsThread
        baseUrl={`/lessons/${courseId}/${data.sub_topic_id}/${lessonId}/comments`}
        canToggle={user.role === "teacher" || user.role === "admin"}
        canModerate={user.role === "teacher" || user.role === "admin"}
        onToggle={async (enabled) => {
          await api.put(
            `/courses/${courseId}/sections/${data.section_id}/sub-topics/${data.sub_topic_id}/comments-toggle`,
            { comments_enabled: enabled }
          );
        }}
      />

      <div className="flex items-center justify-between pt-4 border-t border-zinc-200">
        {prev_lesson_id ? (
          <Link to={`/app/courses/${courseId}/lessons/${prev_lesson_id}`} data-testid="lesson-prev-button" className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-semibold border border-zinc-300 hover:bg-zinc-100">
            <ArrowLeft className="w-4 h-4" /> Previous
          </Link>
        ) : <span />}
        {user.role === "student" && (
          <button onClick={markComplete} data-testid="lesson-mark-complete" className="px-4 py-2 text-sm font-semibold bg-blue-700 text-white hover:bg-blue-900">
            Mark complete
          </button>
        )}
        {next_lesson_id ? (
          <Link to={`/app/courses/${courseId}/lessons/${next_lesson_id}`} data-testid="lesson-next-button" className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-semibold bg-zinc-950 text-white hover:bg-zinc-800">
            Next <ArrowRight className="w-4 h-4" />
          </Link>
        ) : <span data-testid="lesson-final" className="text-xs text-zinc-400">Final lesson</span>}
      </div>
    </div>
  );
}
