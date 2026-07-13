import { useState } from "react";
import { Link, useSearchParams, useNavigate } from "react-router-dom";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { GraduationCap } from "lucide-react";
import { ACADEMY_NAME } from "@/lib/config";

export default function ResetPassword() {
  const [params] = useSearchParams();
  const token = params.get("token") || "";
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    if (password !== confirm) {
      setError("Passwords do not match");
      return;
    }
    setBusy(true);
    try {
      await api.post("/auth/reset-password", { token, password });
      toast.success("Password reset successful — log in with your new password");
      navigate("/auth?mode=login");
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
        <span className="font-heading font-black tracking-tight text-sm sm:text-base leading-tight">{ACADEMY_NAME}</span>
      </Link>
      <div className="w-full max-w-sm bg-white border border-zinc-200 p-8">
        <h1 className="font-heading text-2xl font-black tracking-tight">Set a new password</h1>
        {!token ? (
          <p className="text-sm text-red-600 mt-4" data-testid="reset-no-token">This reset link is invalid. Please request a new one from the <Link to="/forgot-password" className="font-semibold underline">forgot password</Link> page.</p>
        ) : (
          <form onSubmit={submit} className="mt-6 space-y-4">
            <div>
              <label className="text-xs uppercase tracking-[0.2em] font-semibold text-zinc-500">New password</label>
              <input
                data-testid="reset-password-input"
                type="password"
                required
                minLength={6}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="mt-1.5 w-full border border-zinc-300 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-700"
                placeholder="At least 6 characters"
              />
            </div>
            <div>
              <label className="text-xs uppercase tracking-[0.2em] font-semibold text-zinc-500">Confirm password</label>
              <input
                data-testid="reset-confirm-input"
                type="password"
                required
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                className="mt-1.5 w-full border border-zinc-300 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-700"
                placeholder="Repeat password"
              />
            </div>
            {error && <p className="text-sm text-red-600 border border-red-200 bg-red-50 px-3 py-2" data-testid="reset-error">{error}</p>}
            <button data-testid="reset-submit-button" disabled={busy} className="w-full bg-blue-700 text-white py-3 font-semibold hover:bg-blue-900 transition-colors disabled:opacity-50">
              {busy ? "Resetting…" : "Reset password"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
