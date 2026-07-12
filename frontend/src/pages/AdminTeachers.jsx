import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { GraduationCap, BookOpen, Users, FileQuestion, ClipboardList, Radio, ChevronRight, ChevronDown } from "lucide-react";
import dayjs from "dayjs";

export default function AdminTeachers() {
  const [teachers, setTeachers] = useState([]);
  const [expanded, setExpanded] = useState(null);
  const [detail, setDetail] = useState(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  useEffect(() => {
    api.get("/admin/teachers").then((r) => setTeachers(r.data));
  }, []);

  const toggle = async (id) => {
    if (expanded === id) {
      setExpanded(null);
      setDetail(null);
      return;
    }
    setExpanded(id);
    setLoadingDetail(true);
    setDetail(null);
    try {
      const { data } = await api.get(`/admin/teachers/${id}/detail`);
      setDetail(data);
    } finally {
      setLoadingDetail(false);
    }
  };

  return (
    <div className="space-y-6" data-testid="admin-teachers-page">
      <div>
        <p className="text-xs uppercase tracking-[0.2em] font-semibold text-red-600">Admin Panel</p>
        <h1 className="font-heading text-3xl font-black tracking-tight mt-1">Teachers</h1>
        <p className="text-sm text-zinc-500 mt-2">Per-teacher breakdown of courses, students, tests, live classes and assignments.</p>
      </div>

      {teachers.length === 0 && <p className="text-sm text-zinc-500" data-testid="admin-teachers-empty">No teachers found.</p>}

      <div className="border border-zinc-200 divide-y divide-zinc-200">
        {teachers.map((t) => (
          <div key={t.id} data-testid={`teacher-row-${t.id}`}>
            <button
              onClick={() => toggle(t.id)}
              data-testid={`teacher-expand-${t.id}`}
              className="w-full text-left px-5 py-4 flex items-center gap-3 hover:bg-zinc-50 transition-colors"
            >
              {expanded === t.id ? <ChevronDown className="w-4 h-4 shrink-0" /> : <ChevronRight className="w-4 h-4 shrink-0" />}
              <div className="w-10 h-10 bg-blue-50 flex items-center justify-center shrink-0">
                <GraduationCap className="w-5 h-5 text-blue-700" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="font-semibold text-sm">{t.name}</div>
                <div className="text-xs text-zinc-500">
                  {t.email}
                  {t.phone && (
                    <>
                      {" · "}
                      <a
                        href={`https://wa.me/${t.phone.replace(/[^\d+]/g, "")}`}
                        target="_blank"
                        rel="noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        className="text-blue-700 hover:underline"
                        data-testid={`teacher-phone-${t.id}`}
                      >
                        {t.phone}
                      </a>
                    </>
                  )}
                </div>
              </div>
              <div className="hidden sm:flex gap-6 text-xs">
                <Stat icon={BookOpen} label="Courses" value={t.courses} />
                <Stat icon={Users} label="Students" value={t.students} />
                <Stat icon={FileQuestion} label="Tests" value={t.tests} />
                <Stat icon={ClipboardList} label="Assignments" value={t.assignments} />
                <Stat icon={Radio} label="Classes" value={`${t.upcoming_classes}↑ / ${t.past_classes}↓`} />
              </div>
            </button>
            {expanded === t.id && (
              <div className="px-5 pb-6 pt-2 bg-zinc-50 space-y-4" data-testid={`teacher-detail-${t.id}`}>
                {loadingDetail && <p className="text-xs text-zinc-500">Loading…</p>}
                {detail && (
                  <>
                    <DetailBlock title={`Courses (${detail.courses.length})`}>
                      {detail.courses.length === 0 ? (
                        <Empty label="No courses" />
                      ) : (
                        <ul className="text-sm">
                          {detail.courses.map((c) => (
                            <li key={c.id} className="py-1.5 flex justify-between border-b border-zinc-100 last:border-0">
                              <span>{c.title} <span className="text-xs text-zinc-500">· {c.subject}</span></span>
                              <span className="text-xs text-zinc-500">{c.students} students {c.published ? "· published" : "· draft"}</span>
                            </li>
                          ))}
                        </ul>
                      )}
                    </DetailBlock>
                    <DetailBlock title={`Tests (${detail.tests.length})`}>
                      {detail.tests.length === 0 ? <Empty label="No tests" /> : (
                        <ul className="text-sm">
                          {detail.tests.map((t) => (
                            <li key={t.id} className="py-1.5 flex justify-between border-b border-zinc-100 last:border-0">
                              <span>{t.title} <span className="text-xs text-zinc-500">· {t.subject} · {t.course_name || "For all students"}</span></span>
                              <span className="text-xs text-zinc-500">{t.attempts} attempts</span>
                            </li>
                          ))}
                        </ul>
                      )}
                    </DetailBlock>
                    <DetailBlock title={`Live Classes (${detail.live_classes.length})`}>
                      {detail.live_classes.length === 0 ? <Empty label="No live classes" /> : (
                        <ul className="text-sm">
                          {detail.live_classes.map((c) => {
                            const past = c.start_time && c.start_time < new Date().toISOString();
                            return (
                              <li key={c.id} className="py-1.5 flex justify-between border-b border-zinc-100 last:border-0">
                                <span>{c.title} <span className="text-xs text-zinc-500">· {c.subject} · {c.course_name || "For all students"}{c.batch_name ? ` · ${c.batch_name}` : ""}</span></span>
                                <span className="text-xs text-zinc-500">
                                  {c.start_time ? dayjs(c.start_time).format("D MMM, h:mm A") : "—"} · {past ? "past" : "upcoming"}
                                </span>
                              </li>
                            );
                          })}
                        </ul>
                      )}
                    </DetailBlock>
                    <DetailBlock title={`Assignments (${detail.assignments.length})`}>
                      {detail.assignments.length === 0 ? <Empty label="No assignments" /> : (
                        <ul className="text-sm">
                          {detail.assignments.map((a) => (
                            <li key={a.id} className="py-1.5 flex justify-between border-b border-zinc-100 last:border-0">
                              <span>{a.title} <span className="text-xs text-zinc-500">· {a.subject} · {a.course_name || "For all students"}</span></span>
                              <span className="text-xs text-zinc-500">{a.due_date ? `Due ${dayjs(a.due_date).format("D MMM")}` : ""}</span>
                            </li>
                          ))}
                        </ul>
                      )}
                    </DetailBlock>
                  </>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function Stat({ icon: Icon, label, value }) {
  return (
    <div className="flex items-center gap-1.5 text-zinc-600">
      <Icon className="w-3.5 h-3.5" />
      <span className="font-semibold">{value}</span>
      <span className="text-zinc-400">{label}</span>
    </div>
  );
}

function DetailBlock({ title, children }) {
  return (
    <div className="border border-zinc-200 bg-white">
      <div className="px-4 py-2.5 border-b border-zinc-200 bg-zinc-50 font-semibold text-xs uppercase tracking-[0.1em]">{title}</div>
      <div className="px-4 py-2">{children}</div>
    </div>
  );
}

function Empty({ label }) {
  return <p className="text-xs text-zinc-400 py-2">{label}</p>;
}
