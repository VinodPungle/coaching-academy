// Fullscreen-style modal video player (react-player based — YouTube/direct
// file URLs only, no Drive support here; compare with the more capable
// LessonVideoPlayer.jsx which handles Drive too). Auto-marks a lesson
// complete once the student has watched 90% of it.
import { useRef, useState } from "react";
import ReactPlayer from "react-player";
import { X, CheckCircle2, Circle } from "lucide-react";

export default function VideoPlayerModal({ lesson, completed, canComplete, onComplete, onClose }) {
  const firedRef = useRef(false);
  const [done, setDone] = useState(completed);

  const markDone = () => {
    if (firedRef.current || done) return;
    firedRef.current = true;
    setDone(true);
    onComplete();
  };

  const handleProgress = ({ played }) => {
    if (canComplete && played >= 0.9) markDone();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-zinc-950/85 p-4" data-testid="video-player-modal">
      <div className="w-full max-w-4xl">
        <div className="flex items-center justify-between mb-3">
          <div className="min-w-0">
            <p className="text-[10px] uppercase tracking-[0.25em] text-zinc-400 font-semibold">Now playing</p>
            <h2 className="font-heading font-bold text-white truncate" data-testid="video-player-title">{lesson.title}</h2>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {canComplete && (
              <button
                onClick={markDone}
                disabled={done}
                data-testid="video-mark-complete-button"
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold transition-colors ${
                  done ? "bg-green-600 text-white cursor-default" : "border border-zinc-500 text-zinc-200 hover:bg-zinc-800"
                }`}
              >
                {done ? <CheckCircle2 className="w-3.5 h-3.5" /> : <Circle className="w-3.5 h-3.5" />}
                {done ? "Completed" : "Mark complete"}
              </button>
            )}
            <button onClick={onClose} data-testid="video-player-close" className="p-2 text-zinc-300 hover:text-white hover:bg-zinc-800 transition-colors">
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>
        <div className="relative bg-black" style={{ paddingTop: "56.25%" }}>
          <ReactPlayer
            url={lesson.url}
            controls
            playing
            width="100%"
            height="100%"
            style={{ position: "absolute", top: 0, left: 0 }}
            onProgress={handleProgress}
            onEnded={() => canComplete && markDone()}
          />
        </div>
        <p className="mt-2 text-xs text-zinc-400">
          {canComplete
            ? done
              ? "This lesson is marked complete."
              : "Watch 90% of the video and it will be marked complete automatically."
            : "Preview mode — progress is tracked for enrolled students."}
        </p>
      </div>
    </div>
  );
}
