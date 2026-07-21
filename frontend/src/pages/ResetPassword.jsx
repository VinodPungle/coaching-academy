// Step 2 of password reset ("/reset-password?token=..."). The token comes
// from the link emailed by ForgotPassword's flow; if it's missing from the
// URL the form is replaced with an error pointing back to that page. On
// submit, POSTs { token, password } to /auth/reset-password.
import { useState } from "react";
import { Link, useSearchParams, useNavigate } from "react-router-dom";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { GraduationCap, Eye, EyeOff } from "lucide-react";
import { useSiteConfig } from "@/context/SiteConfigContext";

export default function ResetPassword() {
  const [params] = useSearchParams();
  const token = params.get("token") || "";
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const navigate = useNavigate();
  const { brand_name } = useSiteConfig();

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
        <span className="font-heading font-black tracking-tight text-sm sm:text-base leading-tight">{brand_name}</span>
      </Link>
      <div className="w-full max-w-sm bg-white border border-zinc-200 p-8">
        <h1 className="font-heading text-2xl font-black tracking-tight">Set a new password</h1>
        {!token ? (
          <p className="text-sm text-red-600 mt-4" data-testid="reset-no-token">This reset link is invalid. Please request a new one from the <Link to="/forgot-password" className="font-semibold underline">forgot password</Link> page.</p>
        ) : (
          <form onSubmit={submit} className="mt-6 space-y-4">
            <div>
              <label className="text-xs uppercase tracking-[0.2em] font-semibold text-zinc-500">New password</label>
              <div className="relative mt-1.5">
                <input
                  data-testid="reset-password-input"
                  type={showPassword ? "text" : "password"}
                  required
                  minLength={6}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full border border-zinc-300 px-3 py-2.5 pr-10 text-sm focus:outline-none focus:ring-2 focus:ring-blue-700"
                  placeholder="At least 6 characters"
                />
                <button
                  type="button"
                  data-testid="reset-password-toggle"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  title={showPassword ? "Hide password" : "Show password"}
                  className="absolute inset-y-0 right-0 flex items-center px-3 text-zinc-400 hover:text-zinc-950"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>
            <div>
              <label className="text-xs uppercase tracking-[0.2em] font-semibold text-zinc-500">Confirm password</label>
              <div className="relative mt-1.5">
                <input
                  data-testid="reset-confirm-input"
                  type={showConfirm ? "text" : "password"}
                  required
                  value={confirm}
                  onChange={(e) => setConfirm(e.target.value)}
                  className="w-full border border-zinc-300 px-3 py-2.5 pr-10 text-sm focus:outline-none focus:ring-2 focus:ring-blue-700"
                  placeholder="Repeat password"
                />
                <button
                  type="button"
                  data-testid="reset-confirm-toggle"
                  onClick={() => setShowConfirm(!showConfirm)}
                  aria-label={showConfirm ? "Hide password" : "Show password"}
                  title={showConfirm ? "Hide password" : "Show password"}
                  className="absolute inset-y-0 right-0 flex items-center px-3 text-zinc-400 hover:text-zinc-950"
                >
                  {showConfirm ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
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
