// Central axios instance + small helpers used by every page's API calls.
// REACT_APP_BACKEND_URL is baked into the bundle at build time (CRA
// convention) — changing it requires a rebuild, not just an env var flip.
import axios from "axios";

export const api = axios.create({
  baseURL: `${process.env.REACT_APP_BACKEND_URL}/api`,
});

// Attach the JWT to every outgoing request automatically, so individual
// pages never have to remember to pass an Authorization header themselves.
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("jam_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Normalizes FastAPI's `detail` field (a plain string, a list of Pydantic
// validation errors, or a single error object) into one display string —
// wrap every catch block with this before showing a toast.error(...).
export function formatApiError(err) {
  const detail = err?.response?.data?.detail;
  if (detail == null) return err?.message || "Something went wrong. Please try again.";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail))
    return detail.map((e) => (e && typeof e.msg === "string" ? e.msg : JSON.stringify(e))).filter(Boolean).join(" ");
  if (detail && typeof detail.msg === "string") return detail.msg;
  return String(detail);
}

// Turns a backend-relative URL (e.g. "/api/files/{id}") into an absolute
// one pointing at the API origin; passes external (http/https) URLs through
// unchanged. Needed because the frontend and backend are separately
// deployed/hosted — a relative path would otherwise resolve against the
// frontend's own domain.
export function fileUrl(url) {
  if (!url) return "";
  return url.startsWith("/") ? `${process.env.REACT_APP_BACKEND_URL}${url}` : url;
}

// Shared upload helper — POSTs to the generic /files/upload endpoint
// (backend/routers/files.py) with optional upload-progress reporting.
// Used for lesson videos/notes, syllabi, profile photos, etc.
export async function uploadFile(file, onProgress) {
  const fd = new FormData();
  fd.append("file", file);
  const { data } = await api.post("/files/upload", fd, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress: onProgress ? (e) => {
      if (e.total) onProgress(Math.round((e.loaded / e.total) * 100));
    } : undefined,
  });
  return data;
}
