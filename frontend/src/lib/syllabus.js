// Client-side validation for course syllabus uploads.
// Mirrors the backend limits in backend/routers/files.py (DOC_MAX) and the
// PDF-only rule enforced by PUT /courses/{id}/syllabus.

export const SYLLABUS_MAX_BYTES = 25 * 1024 * 1024; // matches backend DOC_MAX

// Returns an error message string, or null when the file is a valid syllabus PDF.
export function syllabusFileError(file) {
  if (!file) return "No file selected";
  if (!/\.pdf$/i.test(file.name || "")) return "Syllabus must be a PDF file";
  if (file.size > SYLLABUS_MAX_BYTES) return "Syllabus PDF is too large (max 25 MB)";
  return null;
}
