import { useState } from "react";
import { Link } from "react-router-dom";
import { api, formatApiError } from "@/lib/api";
import { GraduationCap, MailCheck } from "lucide-react";
import { ACADEMY_NAME } from "@/lib/config";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api.post("/auth/forgot-password", { email });
      setSent(true);
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-zinc-50 px-4">
      <Link to="/" className="flex items-center gap-2 mb-8">
        <GraduationCap className="w-6 h-6 text-blue-700" />
        <span className="font-heading font-black tracking-tight text-lg">{ACADEMY_NAME}</span>
      </Link>
      <div className="w-full max-w-sm bg-white border border-zinc-200 p-8">
        {sent ? (
          <div className="text-center" data-testid="forgot-password-success">
            <MailCheck className="w-10 h-10 text-green-600 mx-auto" strokeWidth={1.5} />
            <h1 className="font-heading text-xl font-black mt-4">Check your inbox</h1>
            <p className="text-sm text-zinc-500 mt-2 leading-relaxed">
              If an account exists for <span className="font-semibold text-zinc-950">{email}</span>, we've emailed a password reset link. It expires in 1 hour.
            </p>
            <Link to="/auth?mode=login" className="mt-6 inline-block text-sm font-semibold text-blue-700 hover:underline">← Back to login</Link>
          </div>
        ) : (
          <>
            <h1 className="font-heading text-2xl font-black tracking-tight">Forgot password?</h1>
            <p className="text-sm text-zinc-500 mt-2">Enter your email and we'll send you a reset link.</p>
            <form onSubmit={submit} className="mt-6 space-y-4">
              <div>
                <label className="text-xs uppercase tracking-[0.2em] font-semibold text-zinc-500">Email</label>
                <input
                  data-testid="forgot-email-input"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="mt-1.5 w-full border border-zinc-300 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-700"
                  placeholder="you@example.com"
                />
              </div>
              {error && <p className="text-sm text-red-600 border border-red-200 bg-red-50 px-3 py-2" data-testid="forgot-error">{error}</p>}
              <button data-testid="forgot-submit-button" disabled={busy} className="w-full bg-blue-700 text-white py-3 font-semibold hover:bg-blue-900 transition-colors disabled:opacity-50">
                {busy ? "Sending…" : "Send reset link"}
              </button>
            </form>
            <Link to="/auth?mode=login" className="mt-4 inline-block text-sm text-zinc-500 hover:text-zinc-950">← Back to login</Link>
          </>
        )}
      </div>
    </div>
  );
}
