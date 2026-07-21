// On-demand viewer for a past live class's recording
// ("/app/live/:id/recording") — same video player + comments pattern as
// LessonPage.jsx, but sourced from a live_classes doc's recording_url
// (set by the teacher via LiveClasses.jsx) instead of a course lesson.
import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { ArrowLeft } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import LessonVideoPlayer from "@/components/LessonVideoPlayer";
import CommentsThread from "@/components/CommentsThread";
import dayjs from "dayjs";

export default function RecordingPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const [live, setLive] = useState(null);

  useEffect(() => {
    api.get(`/live-classes/${id}`).then((r) => setLive(r.data)).catch((err) => toast.error(formatApiError(err)));
  }, [id]);

  if (!live) return <p className="text-sm text-zinc-500" data-testid="recording-loading">Loading recording…</p>;

  if (!live.recording_url) {
    return (
      <div className="max-w-3xl" data-testid="recording-page">
        <Link to="/app/live" className="inline-flex items-center gap-1.5 text-sm text-zinc-500 hover:text-zinc-950">
          <ArrowLeft className="w-4 h-4" /> Back to live classes
        </Link>
        <p className="mt-6 text-sm text-zinc-500">No recording is available for this class yet.</p>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6" data-testid="recording-page">
      <Link to="/app/live" className="inline-flex items-center gap-1.5 text-sm text-zinc-500 hover:text-zinc-950">
        <ArrowLeft className="w-4 h-4" /> Back to live classes
      </Link>

      <div>
        <p className="text-xs uppercase tracking-[0.2em] font-semibold text-zinc-400">Recording · {live.subject}</p>
        <h1 className="font-heading text-3xl font-black tracking-tight mt-1" data-testid="recording-title">{live.title}</h1>
        <p className="text-xs text-zinc-500 mt-1">
          Held on {dayjs(live.start_time).format("D MMM YYYY · h:mm A")} · by {live.teacher_name}
        </p>
      </div>

      <LessonVideoPlayer url={live.recording_url} canTrackProgress={false} />

      <CommentsThread
        baseUrl={`/recordings/${id}/comments`}
        canToggle={user.role === "teacher" || user.role === "admin"}
        canModerate={user.role === "teacher" || user.role === "admin"}
        onToggle={async (enabled) => {
          await api.put(`/live-classes/${id}/comments-toggle`, { comments_enabled: enabled });
        }}
      />
    </div>
  );
}
