import axios from "axios";

export const api = axios.create({
  baseURL: `${process.env.REACT_APP_BACKEND_URL}/api`,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("jam_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export function formatApiError(err) {
  const detail = err?.response?.data?.detail;
  if (detail == null) return err?.message || "Something went wrong. Please try again.";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail))
    return detail.map((e) => (e && typeof e.msg === "string" ? e.msg : JSON.stringify(e))).filter(Boolean).join(" ");
  if (detail && typeof detail.msg === "string") return detail.msg;
  return String(detail);
}

export function fileUrl(url) {
  if (!url) return "";
  return url.startsWith("/") ? `${process.env.REACT_APP_BACKEND_URL}${url}` : url;
}

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
