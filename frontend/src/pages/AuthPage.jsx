import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { formatApiError } from "@/lib/api";
import { GraduationCap } from "lucide-react";
import { ACADEMY_NAME } from "@/lib/config";

export default function AuthPage() {
  const [params] = useSearchParams();
  const [mode, setMode] = useState(params.get("mode") === "register" ? "register" : "login");
  const [role, setRole] = useState(params.get("role") === "teacher" ? "teacher" : "student");
  const [form, setForm] = useState({ name: "", email: "", password: "", phone: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const { login, register } = useAuth();
  const navigate = useNavigate();

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const user =
        mode === "login"
          ? await login(form.email, form.password)
          : await register({ ...form, role });
      navigate(user.role === "student" ? "/app/dashboard" : "/app/dashboard");
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-2 bg-white text-zinc-950">
      <div className="flex flex-col px-6 py-8 md:px-16 md:py-12">
        <Link to="/" className="flex items-center gap-2 w-fit" data-testid="auth-home-link">
          <GraduationCap className="w-6 h-6 text-blue-700" />
          <span className="font-heading font-black tracking-tight text-lg">{ACADEMY_NAME}</span>
        </Link>
        <div className="flex-1 flex items-center">
          <div className="w-full max-w-sm">
            <h1 className="font-heading text-3xl font-black tracking-tight">
              {mode === "login" ? "Welcome back" : "Create your account"}
            </h1>
            <p className="text-sm text-zinc-500 mt-2">
              {mode === "login" ? "Log in to continue your preparation." : "Start your IIT-JAM journey today."}
            </p>

            <form onSubmit={submit} className="mt-8 space-y-4">
              {mode === "register" && (
                <>
                  <div className="grid grid-cols-2 gap-px bg-zinc-200 border border-zinc-200">
                    {["student", "teacher"].map((r) => (
                      <button
                        key={r}
                        type="button"
                        data-testid={`role-select-${r}`}
                        onClick={() => setRole(r)}
                        className={`py-2.5 text-sm font-semibold capitalize transition-colors ${
                          role === r ? "bg-blue-700 text-white" : "bg-white text-zinc-500 hover:bg-zinc-50"
                        }`}
                      >
                        {r}
                      </button>
                    ))}
                  </div>
                  <div>
                    <label className="text-xs uppercase tracking-[0.2em] font-semibold text-zinc-500">Full name</label>
                    <input
                      data-testid="register-name-input"
                      required
                      value={form.name}
                      onChange={set("name")}
                      className="mt-1.5 w-full border border-zinc-300 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-700"
                      placeholder="Rahul Verma"
                    />
                  </div>
                  <div>
                    <label className="text-xs uppercase tracking-[0.2em] font-semibold text-zinc-500">WhatsApp number (optional)</label>
                    <input
                      data-testid="register-phone-input"
                      type="tel"
                      value={form.phone}
                      onChange={set("phone")}
                      className="mt-1.5 w-full border border-zinc-300 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-700"
                      placeholder="+919876543210"
                    />
                  </div>
                </>
              )}
              <div>
                <label className="text-xs uppercase tracking-[0.2em] font-semibold text-zinc-500">Email</label>
                <input
                  data-testid="auth-email-input"
                  type="email"
                  required
                  value={form.email}
                  onChange={set("email")}
                  className="mt-1.5 w-full border border-zinc-300 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-700"
                  placeholder="you@example.com"
                />
              </div>
              <div>
                <div className="flex items-center justify-between">
                  <label className="text-xs uppercase tracking-[0.2em] font-semibold text-zinc-500">Password</label>
                  {mode === "login" && (
                    <Link to="/forgot-password" data-testid="forgot-password-link" className="text-xs font-semibold text-blue-700 hover:underline">
                      Forgot password?
                    </Link>
                  )}
                </div>
                <input
                  data-testid="auth-password-input"
                  type="password"
                  required
                  value={form.password}
                  onChange={set("password")}
                  className="mt-1.5 w-full border border-zinc-300 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-700"
                  placeholder="••••••••"
                />
              </div>
              {error && (
                <p data-testid="auth-error-message" className="text-sm text-red-600 border border-red-200 bg-red-50 px-3 py-2">
                  {error}
                </p>
              )}
              <button
                data-testid="auth-submit-button"
                disabled={busy}
                className="w-full bg-blue-700 text-white py-3 font-semibold hover:bg-blue-900 transition-colors disabled:opacity-50"
              >
                {busy ? "Please wait…" : mode === "login" ? "Log in" : "Create account"}
              </button>
            </form>

            <p className="mt-6 text-sm text-zinc-500">
              {mode === "login" ? `New to ${ACADEMY_NAME}?` : "Already have an account?"}{" "}
              <button
                data-testid="auth-mode-toggle"
                onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(""); }}
                className="font-semibold text-blue-700 hover:underline"
              >
                {mode === "login" ? "Create an account" : "Log in"}
              </button>
            </p>
            <div className="mt-8 border border-zinc-200 bg-zinc-50 p-4 text-xs text-zinc-500 space-y-1">
              <p className="font-semibold uppercase tracking-[0.15em]">Demo accounts</p>
              <p>Student: student@jamacademy.com / Student@123</p>
              <p>Teacher: teacher@jamacademy.com / Teacher@123</p>
            </div>
          </div>
        </div>
      </div>
      <div className="hidden lg:block relative">
        <img
          src="https://images.pexels.com/photos/8199134/pexels-photo-8199134.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940"
          alt="Professor teaching"
          className="absolute inset-0 w-full h-full object-cover"
        />
        <div className="absolute inset-0 bg-zinc-950/50" />
        <div className="absolute bottom-12 left-12 right-12 text-white">
          <p className="font-heading text-2xl font-bold leading-snug">
            "The mock test series felt exactly like the real JAM paper. I walked into the exam hall with zero surprises."
          </p>
          <p className="mt-3 text-sm text-zinc-300">— AIR 14, IIT-JAM Physics</p>
        </div>
      </div>
    </div>
  );
}
