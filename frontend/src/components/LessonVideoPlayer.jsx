import { useRef, useState } from "react";
import ReactPlayer from "react-player";
import { AlertTriangle, ExternalLink } from "lucide-react";
import { detectVideoProvider, toDriveEmbedUrl } from "@/lib/video";
import { fileUrl as toAbsoluteFileUrl } from "@/lib/api";

/**
 * Lesson video player: handles YouTube (react-player), Google Drive (iframe), and direct file URLs.
 * Auto-marks the lesson complete once 90% of the video has been watched (for react-player-supported URLs).
 * For Drive iframe playback, the caller should render a "Mark complete" button since we cannot observe progress.
 */
export default function LessonVideoPlayer({ url, onProgress90, canTrackProgress = true }) {
  const firedRef = useRef(false);
  const [driveError, setDriveError] = useState(false);
  const provider = detectVideoProvider(url);

  const handleProgress = ({ played }) => {
    if (canTrackProgress && played >= 0.9 && !firedRef.current) {
      firedRef.current = true;
      onProgress90?.();
    }
  };

  if (!url) return null;

  if (provider === "drive") {
    const embed = toDriveEmbedUrl(url);
    if (!embed) {
      return (
        <InvalidLinkNotice url={url} reason="This Google Drive link isn't in a format we recognise. Share the file with 'Anyone with the link' and paste the /file/d/... link." />
      );
    }
    return (
      <div className="relative bg-black aspect-video" data-testid="lesson-drive-player">
        {driveError ? (
          <InvalidLinkNotice url={url} reason="The Drive file couldn't be embedded. Verify that sharing is set to 'Anyone with the link' — not restricted." />
        ) : (
          <iframe
            src={embed}
            title="Video"
            allow="autoplay; encrypted-media; fullscreen"
            allowFullScreen
            onError={() => setDriveError(true)}
            className="absolute inset-0 w-full h-full"
            data-testid="lesson-drive-iframe"
          />
        )}
      </div>
    );
  }

  // YouTube + direct URLs — react-player handles both, with progress tracking
  return (
    <div className="relative bg-black aspect-video" data-testid="lesson-reactplayer">
      <ReactPlayer
        url={url}
        controls
        width="100%"
        height="100%"
        style={{ position: "absolute", top: 0, left: 0 }}
        onProgress={handleProgress}
        onEnded={() => canTrackProgress && !firedRef.current && (firedRef.current = true) && onProgress90?.()}
      />
    </div>
  );
}

function InvalidLinkNotice({ url, reason }) {
  return (
    <div className="border border-amber-300 bg-amber-50 p-6 text-amber-900" data-testid="lesson-video-invalid">
      <div className="flex items-start gap-3">
        <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" />
        <div>
          <p className="font-semibold text-sm">This video can't be played inline</p>
          <p className="text-xs mt-1 text-amber-800">{reason}</p>
          <a href={url} target="_blank" rel="noreferrer" className="mt-3 inline-flex items-center gap-1 text-xs font-semibold text-amber-900 hover:underline">
            Open the link directly <ExternalLink className="w-3 h-3" />
          </a>
        </div>
      </div>
    </div>
  );
}
h-3" />
          </a>
        </div>
      </div>
    </div>
  );
}
