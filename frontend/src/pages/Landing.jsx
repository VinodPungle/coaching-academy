import { Link } from "react-router-dom";
import { GraduationCap, Radio, FileQuestion, BarChart3, BookOpen, Award, ArrowRight, Users } from "lucide-react";
import { ACADEMY_NAME } from "@/lib/config";

const FEATURES = [
  { icon: Radio, title: "Live Classes", desc: "Interactive live sessions with IIT alumni faculty, auto-recorded for revision." },
  { icon: BookOpen, title: "Structured Courses", desc: "Video lectures, PDF notes and practice sheets organised chapter-wise for every JAM paper." },
  { icon: FileQuestion, title: "Mock Test Series", desc: "Timed, JAM-pattern mock tests with instant auto-evaluation and detailed scorecards." },
  { icon: BarChart3, title: "Progress Analytics", desc: "Track lesson completion, test percentile and weak areas in real time." },
  { icon: Users, title: "Assignments & Feedback", desc: "Weekly assignments graded personally by faculty with written feedback." },
  { icon: Award, title: "Result Oriented", desc: "A curriculum reverse-engineered from 10 years of JAM papers." },
];

const SUBJECTS = ["Physics", "Chemistry", "Mathematics", "Biotechnology", "Economics", "Geology"];

export default function Landing() {
  return (
    <div className="min-h-screen bg-white text-zinc-950">
      <header className="sticky top-0 z-50 bg-white/80 backdrop-blur-xl border-b border-zinc-200/50">
        <div className="max-w-6xl mx-auto flex items-center justify-between px-4 md:px-8 h-16">
          <div className="flex items-center gap-2">
            <GraduationCap className="w-7 h-7 text-blue-700" />
            <span className="font-heading font-black tracking-tight text-xl">{ACADEMY_NAME}</span>
          </div>
          <div className="flex items-center gap-3">
            <Link to="/auth?mode=login" data-testid="header-login-link" className="px-4 py-2 text-sm font-semibold border border-zinc-300 hover:bg-zinc-100 transition-colors">
              Log in
            </Link>
            <Link to="/auth?mode=register" data-testid="header-register-link" className="px-4 py-2 text-sm font-semibold bg-blue-700 text-white hover:bg-blue-900 transition-colors">
              Get started
            </Link>
          </div>
        </div>
      </header>

      <section className="max-w-6xl mx-auto px-4 md:px-8 py-16 md:py-24 grid md:grid-cols-2 gap-12 items-center">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] font-semibold text-red-600 mb-4">IIT-JAM 2027 Batches Open</p>
          <h1 className="font-heading text-4xl sm:text-5xl lg:text-6xl tracking-tighter font-black leading-[1.05]">
            Crack IIT-JAM with the faculty who cracked it first.
          </h1>
          <p className="mt-6 text-base md:text-lg text-zinc-500 leading-relaxed max-w-lg">
            Live classes, structured courses, JAM-pattern mock tests and personal mentorship — everything you need to reach IIT, in one portal.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link to="/auth?mode=register" data-testid="hero-cta-student" className="inline-flex items-center gap-2 px-6 py-3 bg-blue-700 text-white font-semibold hover:bg-blue-900 transition-colors">
              Start learning free <ArrowRight className="w-4 h-4" />
            </Link>
            <Link to="/auth?mode=register&role=teacher" data-testid="hero-cta-teacher" className="inline-flex items-center gap-2 px-6 py-3 border border-zinc-300 font-semibold hover:bg-zinc-100 transition-colors">
              I'm a teacher
            </Link>
          </div>
          <div className="mt-10 flex gap-8">
            {[["1,200+", "Students mentored"], ["94%", "Selection rate"], ["6", "JAM papers covered"]].map(([n, l]) => (
              <div key={l}>
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
          <div className="absolute -bottom-5 -left-5 bg-zinc-950 text-white px-5 py-4 hidden md:block">
            <div className="text-xs uppercase tracking-[0.2em] text-zinc-400">Next live class</div>
            <div className="font-heading font-bold mt-1">Quantum Mechanics — Wave Functions</div>
          </div>
        </div>
      </section>

      <section className="border-y border-zinc-200 bg-zinc-50">
        <div className="max-w-6xl mx-auto px-4 md:px-8 py-6 flex flex-wrap gap-x-8 gap-y-2 items-center justify-center">
          {SUBJECTS.map((s) => (
            <span key={s} className="text-sm font-semibold uppercase tracking-[0.15em] text-zinc-400">{s}</span>
          ))}
        </div>
      </section>

      <section className="max-w-6xl mx-auto px-4 md:px-8 py-16 md:py-24">
        <h2 className="font-heading text-2xl sm:text-3xl lg:text-4xl tracking-tight font-bold max-w-xl">
          Everything a serious JAM aspirant needs. Nothing they don't.
        </h2>
        <div className="mt-12 grid sm:grid-cols-2 lg:grid-cols-3 gap-px bg-zinc-200 border border-zinc-200">
          {FEATURES.map(({ icon: Icon, title, desc }) => (
            <div key={title} className="bg-white p-8 hover:bg-zinc-50 transition-colors">
              <Icon className="w-6 h-6 text-blue-700" strokeWidth={1.5} />
              <h3 className="font-heading font-bold text-lg mt-4">{title}</h3>
              <p className="text-sm text-zinc-500 leading-relaxed mt-2">{desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="bg-zinc-950 text-white">
        <div className="max-w-6xl mx-auto px-4 md:px-8 py-16 md:py-20 flex flex-col md:flex-row items-start md:items-center justify-between gap-8">
          <div>
            <h2 className="font-heading text-2xl sm:text-3xl lg:text-4xl tracking-tight font-bold">Your IIT seat is one decision away.</h2>
            <p className="text-zinc-400 mt-3">Join the JAM 2027 batch today. First course module is free.</p>
          </div>
          <Link to="/auth?mode=register" data-testid="footer-cta" className="shrink-0 inline-flex items-center gap-2 px-6 py-3 bg-white text-zinc-950 font-semibold hover:bg-zinc-200 transition-colors">
            Create free account <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

      <footer className="border-t border-zinc-200">
        <div className="max-w-6xl mx-auto px-4 md:px-8 py-8 text-sm text-zinc-500 flex justify-between">
          <span>© 2026 {ACADEMY_NAME}</span>
          <span>Built for IIT-JAM aspirants</span>
        </div>
      </footer>
    </div>
  );
}
