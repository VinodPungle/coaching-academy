/**
 * Video URL utilities. Handles:
 *  - Google Drive share links → normalise to /preview embed URL
 *  - YouTube share/watch/short links → passed through to react-player which supports them natively
 *  - Direct file URLs (mp4, webm, uploaded to our backend) → passed through
 */

export function detectVideoProvider(url) {
  if (!url) return "empty";
  const u = url.trim().toLowerCase();
  if (u.includes("drive.google.com") || u.includes("docs.google.com")) return "drive";
  if (u.includes("youtube.com") || u.includes("youtu.be")) return "youtube";
  if (u.includes("/api/files/") || /\.(mp4|webm|mov|m4v|ogg)(\?|$)/.test(u)) return "file";
  if (u.startsWith("http") || u.startsWith("/")) return "external";
  return "unknown";
}

/**
 * Convert any Google Drive URL to an embeddable /preview URL.
 * Supported inputs:
 *   https://drive.google.com/file/d/FILE_ID/view?usp=sharing
 *   https://drive.google.com/file/d/FILE_ID/view
 *   https://drive.google.com/file/d/FILE_ID/preview
 *   https://drive.google.com/open?id=FILE_ID
 *   https://drive.google.com/uc?id=FILE_ID&...
 *   https://docs.google.com/uc?id=FILE_ID
 */
export function toDriveEmbedUrl(url) {
  if (!url) return null;
  const raw = url.trim();
  // /file/d/{id}/...
  let m = raw.match(/\/file\/d\/([a-zA-Z0-9_-]+)/);
  if (m) return `https://drive.google.com/file/d/${m[1]}/preview`;
  // ?id={id}
  m = raw.match(/[?&]id=([a-zA-Z0-9_-]+)/);
  if (m) return `https://drive.google.com/file/d/${m[1]}/preview`;
  // /d/{id}
  m = raw.match(/\/d\/([a-zA-Z0-9_-]+)/);
  if (m) return `https://drive.google.com/file/d/${m[1]}/preview`;
  return null;
}

/**
 * Extract Drive file id (for permission-check hints, opening in new tab)
 */
export function driveFileId(url) {
  if (!url) return null;
  const m1 = url.match(/\/file\/d\/([a-zA-Z0-9_-]+)/);
  if (m1) return m1[1];
  const m2 = url.match(/[?&]id=([a-zA-Z0-9_-]+)/);
  if (m2) return m2[1];
  return null;
}
