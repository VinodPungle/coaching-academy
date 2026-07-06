import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api, formatApiError } from "@/lib/api";
import { GraduationCap, Printer, ArrowLeft, Award } from "lucide-react";
import dayjs from "dayjs";
import { ACADEMY_NAME } from "@/lib/config";

export default function Certificate() {
  const { courseId } = useParams();
  const [cert, setCert] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get(`/courses/${courseId}/certificate`)
      .then((r) => setCert(r.data))
      .catch((e) => setError(formatApiError(e)));
  }, [courseId]);

  if (error)
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4 bg-zinc-50 p-6">
        <p className="text-sm text-red-600 border border-red-200 bg-red-50 px-4 py-3" data-testid="certificate-error">{error}</p>
        <Link to="/app/courses" className="text-sm font-semibold text-blue-700 hover:underline">← Back to courses</Link>
      </div>
    );
  if (!cert) return <div className="min-h-screen flex items-center justify-center text-sm text-zinc-500">Loading certificate…</div>;

  return (
    <div className="min-h-screen bg-zinc-100 py-10 px-4">
      <style>{`@media print { .no-print { display: none !important; } body { background: #fff; } .cert-sheet { box-shadow: none !important; margin: 0 !important; } }`}</style>
      <div className="no-print max-w-3xl mx-auto mb-6 flex items-center justify-between">
        <Link to="/app/courses" data-testid="certificate-back-link" className="inline-flex items-center gap-1.5 text-sm text-zinc-500 hover:text-zinc-950">
          <ArrowLeft className="w-4 h-4" /> Back to courses
        </Link>
        <button onClick={() => window.print()} data-testid="certificate-print-button" className="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-semibold bg-blue-700 text-white hover:bg-blue-900 transition-colors">
          <Printer className="w-4 h-4" /> Print / Save as PDF
        </button>
      </div>

      <div className="cert-sheet max-w-3xl mx-auto bg-white shadow-lg border-[3px] border-zinc-950 p-2" data-testid="certificate-sheet">
        <div className="border border-zinc-300 px-10 py-12 text-center relative">
          <div className="absolute top-6 left-6"><Award className="w-8 h-8 text-blue-700" strokeWidth={1.5} /></div>
          <div className="absolute top-6 right-6 text-right">
            <p className="text-[10px] uppercase tracking-[0.2em] text-zinc-400">Certificate No.</p>
            <p className="text-xs font-mono font-bold" data-testid="certificate-number">{cert.cert_no}</p>
          </div>

          <div className="flex items-center justify-center gap-2">
            <GraduationCap className="w-7 h-7 text-blue-700" />
            <span className="font-heading font-black tracking-tight text-xl">{ACADEMY_NAME}</span>
          </div>
          <p className="mt-8 text-xs uppercase tracking-[0.35em] text-zinc-500">Certificate of Completion</p>
          <p className="mt-8 text-sm text-zinc-500">This is to certify that</p>
          <h1 className="font-heading text-4xl font-black tracking-tight mt-3 text-blue-700" data-testid="certificate-student-name">{cert.student_name}</h1>
          <p className="mt-5 text-sm text-zinc-500 max-w-md mx-auto leading-relaxed">
            has successfully completed all lessons and requirements of the course
          </p>
          <h2 className="font-heading text-2xl font-bold mt-3" data-testid="certificate-course-title">{cert.course_title}</h2>
          <p className="mt-2 text-xs uppercase tracking-[0.2em] text-zinc-400">{cert.subject} · IIT-JAM Preparation</p>

          <div className="mt-12 flex items-end justify-between px-4">
            <div className="text-left">
              <p className="text-sm font-semibold border-t border-zinc-300 pt-2">{dayjs(cert.issued_at).format("D MMMM YYYY")}</p>
              <p className="text-[10px] uppercase tracking-[0.2em] text-zinc-400 mt-1">Date of Issue</p>
            </div>
            <div className="text-right">
              <p className="font-heading text-lg font-bold border-t border-zinc-300 pt-2">{cert.teacher_name}</p>
              <p className="text-[10px] uppercase tracking-[0.2em] text-zinc-400 mt-1">Course Instructor</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
