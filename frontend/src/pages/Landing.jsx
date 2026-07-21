// Public marketing homepage (route "/") — hero, feature grid, contact/
// enquiry form (posts to POST /api/enquiries), all editable at runtime via
// SiteConfigContext rather than hardcoded here.
import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import dayjs from "dayjs";
import {
  GraduationCap, Radio, FileQuestion, BarChart3, BookOpen, Award,
  ArrowRight, Users, Mail, Phone, Globe, Send, CheckCircle2,
} from "lucide-react";
import { useSiteConfig } from "@/context/SiteConfigContext";
import { api, formatApiError } from "@/lib/api";

const FEATURES = [
  { icon: Radio, title: "Live Classes", desc: "Interactive live sessions with experienced faculty, auto-recorded for revision." },
  { icon: BookOpen, title: "Structured Courses", desc: "Video lectures, PDF notes and practice sheets organised chapter-wise for every exam." },
  { icon: FileQuestion, title: "Mock Test Series", desc: "Timed, exam-pattern mock tests with instant auto-evaluation and detailed scorecards." },
  { icon: BarChart3, title: "Progress Analytics", desc: "Track lesson completion, test percentile and weak areas in real time." },
  { icon: Users, title: "Assignments & Feedback", desc: "Weekly assignments graded personally by faculty with written feedback." },
  { icon: Award, title: "Result Oriented", desc: "Curriculum reverse-engineered from years of past papers across entrance exams." },
];

function EnquiryForm() {
  // `website` is a honeypot field — see backend/routers/enquiries.py; kept
  // hidden via CSS and never shown to real users.
  const [form, setForm] = useState({ name: "", email: "", phone: "", message: "", website: "" });
  const [status, setStatus] = useState({ state: "idle", message: "" });
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setStatus({ state: "submitting", message: "" });
    try {
      const { data } = await api.post("/enquiries", form);
      setStatus({ state: "success", message: data?.message || "Thank you. We'll get back to you shortly." });
      setForm({ name: "", email: "", phone: "", message: "", website: "" });
    } catch (err) {
      setStatus({ state: "error", message: formatApiError(err) });
    }
  };

  if (status.state === "success") {
    return (
      <div data-testid="enquiry-success" className="border border-emerald-200 bg-emerald-50 p-8">
        <CheckCircle2 className="w-8 h-8 text-emerald-600" strokeWidth={1.5} />
        <h3 className="font-heading font-bold text-lg mt-3 text-emerald-900">Enquiry received</h3>
        <p className="text-sm text-emerald-800 mt-2">{status.message}</p>
        <button type="button" data-testid="enquiry-reset" onClick={() => setStatus({ state: "idle", message: "" })} className="mt-6 text-sm font-semibold text-emerald-800 underline hover:no-underline">
          Send another enquiry
        </button>
      </div>
    );
  }

  return (
    <form onSubmit={submit} className="space-y-4" data-testid="enquiry-form">
      <input type="text" name="website" tabIndex="-1" autoComplete="off" value={form.website} onChange={set("website")} className="hidden" aria-hidden="true" />
      <div className="grid sm:grid-cols-2 gap-4">
        <div>
          <label className="text-xs uppercase tracking-[0.2em] font-semibold text-zinc-500">Full name</label>
          <input data-testid="enquiry-name-input" required minLength={2} value={form.name} onChange={set("name")} className="mt-1.5 w-full border border-zinc-300 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-700" placeholder="Your name" />
        </div>
        <div>
          <label className="text-xs uppercase tracking-[0.2em] font-semibold text-zinc-500">Phone</label>
          <input data-testid="enquiry-phone-input" type="tel" required value={form.phone} onChange={set("phone")} className="mt-1.5 w-full border border-zinc-300 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-700" placeholder="+91 98765 43210" />
        </div>
      </div>
      <div>
        <label className="text-xs uppercase tracking-[0.2em] font-semibold text-zinc-500">Email</label>
        <input data-testid="enquiry-email-input" type="email" required value={form.email} onChange={set("email")} className="mt-1.5 w-full border border-zinc-300 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-700" placeholder="you@example.com" />
      </div>
      <div>
        <label className="text-xs uppercase tracking-[0.2em] font-semibold text-zinc-500">Message</label>
        <textarea data-testid="enquiry-message-input" required minLength={10} rows={5} value={form.message} onChange={set("message")} className="mt-1.5 w-full border border-zinc-300 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-700 resize-none" placeholder="Tell us which exam you're preparing for, and how we can help." />
      </div>
      {status.state === "error" && (
        <p data-testid="enquiry-error" className="text-sm text-red-600 border border-red-200 bg-red-50 px-3 py-2">{status.message}</p>
      )}
      <button data-testid="enquiry-submit-button" type="submit" disabled={status.state === "submitting"} className="inline-flex items-center gap-2 px-6 py-3 bg-blue-700 text-white font-semibold hover:bg-blue-900 transition-colors disabled:opacity-50">
        {status.state === "submitting" ? "Sending…" : "Send enquiry"} <Send className="w-4 h-4" />
      </button>
    </form>
  );
}

export default function Landing() {
  const { brand_name, landing } = useSiteConfig();
  const [nextClass, setNextClass] = useState({ state: "loading", data: null });

  useEffect(() => {
    api.get("/live-classes/public/next")
      .then(({ data }) => setNextClass({ state: "ok", data }))
      .catch(() => setNextClass({ state: "ok", data: null }));
  }, []);

  return (
    <div className="min-h-screen bg-white text-zinc-950">
      <header className="sticky top-0 z-50 bg-white/80 backdrop-blur-xl border-b border-zinc-200/50">
        <div className="max-w-6xl mx-auto flex items-center justify-between px-4 md:px-8 h-16">
          <div className="flex items-center gap-2 min-w-0">
            <GraduationCap className="w-7 h-7 text-blue-700 shrink-0" />
            <span className="font-heading font-black tracking-tight text-sm sm:text-base md:text-lg leading-tight truncate" data-testid="brand-name">{brand_name}</span>
          </div>
          <div className="flex items-center gap-3 shrink-0">
            <Link to="/teachers" data-testid="header-teachers-link" className="hidden sm:inline text-sm font-semibold text-zinc-600 hover:text-zinc-950 px-2 py-2 transition-colors">
              {landing.teachers_menu_label}
            </Link>
            <a href="#contact" data-testid="header-contact-link" className="hidden sm:inline text-sm font-semibold text-zinc-600 hover:text-zinc-950 px-2 py-2 transition-colors">
              Contact
            </a>
            <Link to="/auth?mode=login" data-testid="header-login-link" className="px-4 py-2 text-sm font-semibold border border-zinc-300 hover:bg-zinc-100 transition-colors">Log in</Link>
            <Link to="/auth?mode=register" data-testid="header-register-link" className="px-4 py-2 text-sm font-semibold bg-blue-700 text-white hover:bg-blue-900 transition-colors">Get started</Link>
          </div>
        </div>
      </header>

      <section className="max-w-6xl mx-auto px-4 md:px-8 py-12 md:py-16 grid md:grid-cols-2 gap-10 items-center">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] font-semibold text-red-600 mb-4">{landing.hero_badge}</p>
          <h1 className="font-heading text-4xl sm:text-5xl lg:text-6xl tracking-tighter font-black leading-[1.05]" data-testid="hero-heading">
            {landing.hero_heading}
          </h1>
          <p className="mt-5 text-base md:text-lg text-zinc-500 leading-relaxed max-w-lg" data-testid="hero-subheading">
            {landing.hero_subheading}
          </p>
          <div className="mt-7 flex flex-wrap gap-3">
            <Link to="/auth?mode=register" data-testid="hero-cta-student" className="inline-flex items-center gap-2 px-6 py-3 bg-blue-700 text-white font-semibold hover:bg-blue-900 transition-colors">
              {landing.hero_cta_student} <ArrowRight className="w-4 h-4" />
            </Link>
            <Link to="/auth?mode=register&role=teacher" data-testid="hero-cta-teacher" className="inline-flex items-center gap-2 px-6 py-3 border border-zinc-300 font-semibold hover:bg-zinc-100 transition-colors">
              {landing.hero_cta_teacher}
            </Link>
          </div>
          <div className="mt-8 flex gap-8">
            {[["stat_1", landing.stat_1_number, landing.stat_1_label], ["stat_2", landing.stat_2_number, landing.stat_2_label], ["stat_3", landing.stat_3_number, landing.stat_3_label]].map(([k, n, l]) => (
              <div key={k}>
                <div className="font-heading text-2xl font-black">{n}</div>
                <div className="text-xs uppercase tracking-[0.15em] text-zinc-500 mt-1">{l}</div>
              </div>
            ))}
          </div>
        </div>
        <div className="relative">
          <img
            src="https://images.pexels.com/photos/16420237/pexels-photo-16420237.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940"
            alt="Student studying"
            className="w-full h-[420px] object-cover border border-zinc-200"
          />
          <div className="absolute -bottom-5 -left-5 bg-zinc-950 text-white px-5 py-4 hidden md:block" data-testid="next-class-card">
            <div className="text-xs uppercase tracking-[0.2em] text-zinc-400">Next live class</div>
            {nextClass.state === "loading" ? (
              <div className="font-heading font-bold mt-1 text-sm">Loading…</div>
            ) : nextClass.data ? (
              <>
                <div className="font-heading font-bold mt-1">{nextClass.data.title}</div>
                <div className="text-xs text-zinc-400 mt-1">{dayjs(nextClass.data.start_time).format("ddd, D MMM · h:mm A")}</div>
              </>
            ) : (
              <div className="font-heading font-bold mt-1 text-sm text-zinc-300">{landing.next_class_empty_state}</div>
            )}
          </div>
        </div>
      </section>

      <section className="max-w-6xl mx-auto px-4 md:px-8 py-12 md:py-16">
        <h2 className="font-heading text-2xl sm:text-3xl lg:text-4xl tracking-tight font-bold max-w-xl">
          {landing.features_heading}
        </h2>
        <div className="mt-10 grid sm:grid-cols-2 lg:grid-cols-3 gap-px bg-zinc-200 border border-zinc-200">
          {FEATURES.map(({ icon: Icon, title, desc }) => (
            <div key={title} className="bg-white p-8 hover:bg-zinc-50 transition-colors">
              <Icon className="w-6 h-6 text-blue-700" strokeWidth={1.5} />
              <h3 className="font-heading font-bold text-lg mt-4">{title}</h3>
              <p className="text-sm text-zinc-500 leading-relaxed mt-2">{desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section id="contact" className="border-t border-zinc-200 bg-zinc-50 scroll-mt-20">
        <div className="max-w-6xl mx-auto px-4 md:px-8 py-12 md:py-16 grid md:grid-cols-2 gap-10">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] font-semibold text-blue-700 mb-4">{landing.contact_eyebrow}</p>
            <h2 className="font-heading text-2xl sm:text-3xl lg:text-4xl tracking-tight font-bold">
              {landing.contact_heading}
            </h2>
            <p className="text-base text-zinc-500 mt-4 max-w-md">
              {landing.contact_description}
            </p>
            <div className="mt-8 space-y-5" data-testid="contact-details">
              <a href={`mailto:${landing.contact_email}`} data-testid="contact-email" className="flex items-start gap-4 group">
                <div className="border border-zinc-300 p-3 group-hover:border-blue-700 transition-colors"><Mail className="w-5 h-5 text-blue-700" strokeWidth={1.5} /></div>
                <div>
                  <div className="text-xs uppercase tracking-[0.15em] text-zinc-500 font-semibold">Email</div>
                  <div className="text-sm font-semibold text-zinc-950 mt-1 group-hover:underline break-all">{landing.contact_email}</div>
                </div>
              </a>
              <a href={`tel:${(landing.contact_phone || "").replace(/\s+/g, "")}`} data-testid="contact-phone" className="flex items-start gap-4 group">
                <div className="border border-zinc-300 p-3 group-hover:border-blue-700 transition-colors"><Phone className="w-5 h-5 text-blue-700" strokeWidth={1.5} /></div>
                <div>
                  <div className="text-xs uppercase tracking-[0.15em] text-zinc-500 font-semibold">Phone</div>
                  <div className="text-sm font-semibold text-zinc-950 mt-1 group-hover:underline">{landing.contact_phone}</div>
                </div>
              </a>
              <a href={`https://${landing.contact_website}`} target="_blank" rel="noreferrer" data-testid="contact-website" className="flex items-start gap-4 group">
                <div className="border border-zinc-300 p-3 group-hover:border-blue-700 transition-colors"><Globe className="w-5 h-5 text-blue-700" strokeWidth={1.5} /></div>
                <div>
                  <div className="text-xs uppercase tracking-[0.15em] text-zinc-500 font-semibold">Website</div>
                  <div className="text-sm font-semibold text-zinc-950 mt-1 group-hover:underline">{landing.contact_website}</div>
                </div>
              </a>
            </div>
          </div>
          <div className="bg-white border border-zinc-200 p-6 md:p-8">
            <h3 className="font-heading text-xl font-bold">Send us an enquiry</h3>
            <p className="text-sm text-zinc-500 mt-1">Fill in your details and we&apos;ll reach out to you shortly.</p>
            <div className="mt-6"><EnquiryForm /></div>
          </div>
        </div>
      </section>

      <section className="bg-zinc-950 text-white">
        <div className="max-w-6xl mx-auto px-4 md:px-8 py-12 md:py-14 flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
          <div>
            <h2 className="font-heading text-2xl sm:text-3xl lg:text-4xl tracking-tight font-bold" data-testid="cta-heading">{landing.cta_heading}</h2>
            <p className="text-zinc-400 mt-3">{landing.cta_description}</p>
          </div>
          <Link to="/auth?mode=register" data-testid="footer-cta" className="shrink-0 inline-flex items-center gap-2 px-6 py-3 bg-white text-zinc-950 font-semibold hover:bg-zinc-200 transition-colors">
            {landing.cta_button} <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

      <footer className="border-t border-zinc-200">
        <div className="max-w-6xl mx-auto px-4 md:px-8 py-8 text-sm text-zinc-500 flex flex-wrap gap-4 justify-between">
          <span>© 2026 {brand_name}</span>
          <span>{landing.footer_tagline}</span>
        </div>
      </footer>
    </div>
  );
}
