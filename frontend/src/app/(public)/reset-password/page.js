"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useResetPassword } from "@/features/auth/hooks";
import { getApiErrorMessage } from "@/lib/apiErrors";
import ThemeController from "@/components/shared/others/ThemeController";

export default function ResetPasswordPage() {
  const sp = useSearchParams();
  const token = useMemo(() => (sp.get("token") || "").trim(), [sp]);
  const resetMut = useResetPassword();

  const [form, setForm] = useState({
    new_password: "",
    confirm_password: "",
  });
  const [showPassword, setShowPassword] = useState(false);
  const [formError, setFormError] = useState("");
  const [success, setSuccess] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");

  const isLoading = resetMut.isPending;
  const linkInvalid = !token;

  const labelCls =
    "block text-[12.5px] font-medium text-ds-text-secondary mb-1.5";
  const inputCls =
    "w-full h-11 rounded-lg border border-ds-border " +
    "bg-ds-surface-input px-3.5 text-sm text-ds-text-primary " +
    "placeholder:text-ds-text-muted " +
    "focus:outline-none focus:border-ds-action/50 focus:ring-4 focus:ring-ds-action/10 transition";

  const onChange = (e) => {
    const { name, value } = e.target;
    setFormError("");
    setForm((p) => ({ ...p, [name]: value }));
  };

  const onSubmit = async (e) => {
    e.preventDefault();
    setFormError("");

    if (linkInvalid) {
      setFormError("Invalid or expired password reset link.");
      return;
    }

    if (!form.new_password || form.new_password.length < 6) {
      setFormError("Password must be at least 6 characters.");
      return;
    }

    if (form.new_password !== form.confirm_password) {
      setFormError("Passwords do not match.");
      return;
    }

    try {
      const res = await resetMut.mutateAsync({
        token,
        new_password: form.new_password,
        confirm_password: form.confirm_password,
      });
      setSuccessMessage(res?.message || "Password reset successfully.");
      setSuccess(true);
    } catch (err) {
      setFormError(
        getApiErrorMessage(err, "Invalid or expired password reset link."),
      );
    }
  };

  return (
    <main className="min-h-screen bg-ds-page">
      <ThemeController />
      <div className="min-h-[80vh] flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-md rounded-2xl border border-ds-border bg-ds-surface p-6 md:p-8 shadow-sm">
          <h1 className="text-xl font-semibold text-ds-text-primary">
            Reset password
          </h1>
          <p className="mt-1 text-sm text-ds-text-muted">
            Choose a new password for your JustClick account.
          </p>

          {success ? (
            <div className="mt-6 space-y-4">
              <div
                role="status"
                className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-sm text-ds-text-primary"
              >
                {successMessage}
              </div>
              <Link
                href="/login"
                className="inline-flex h-11 w-full items-center justify-center rounded-lg bg-ds-action text-sm font-semibold text-white hover:bg-ds-action-hover transition"
              >
                Continue to login
              </Link>
            </div>
          ) : linkInvalid ? (
            <div className="mt-6 space-y-4">
              <div
                role="alert"
                className="rounded-xl border border-ds-error/30 bg-ds-error/10 px-4 py-3 text-sm text-ds-error"
              >
                This reset link is invalid or incomplete. Request a new one from
                the forgot password page.
              </div>
              <Link
                href="/forgot-password"
                className="inline-flex h-11 w-full items-center justify-center rounded-lg bg-ds-action text-sm font-semibold text-white hover:bg-ds-action-hover transition"
              >
                Request new link
              </Link>
            </div>
          ) : (
            <form onSubmit={onSubmit} className="mt-6 space-y-3.5">
              {formError ? (
                <div
                  role="alert"
                  className="rounded-xl border border-ds-error/30 bg-ds-error/10 px-4 py-3 text-sm text-ds-error"
                >
                  {formError}
                </div>
              ) : null}

              <div>
                <div className="flex items-center justify-between">
                  <label className={labelCls} htmlFor="new_password">
                    New password <span className="text-ds-error">*</span>
                  </label>
                  <button
                    type="button"
                    onClick={() => setShowPassword((v) => !v)}
                    className="text-xs font-semibold text-ds-action hover:underline"
                    disabled={isLoading}
                  >
                    {showPassword ? "Hide" : "Show"}
                  </button>
                </div>
                <input
                  id="new_password"
                  name="new_password"
                  type={showPassword ? "text" : "password"}
                  value={form.new_password}
                  onChange={onChange}
                  className={inputCls}
                  autoComplete="new-password"
                  disabled={isLoading}
                  placeholder="At least 6 characters"
                />
              </div>

              <div>
                <label className={labelCls} htmlFor="confirm_password">
                  Confirm new password <span className="text-ds-error">*</span>
                </label>
                <input
                  id="confirm_password"
                  name="confirm_password"
                  type={showPassword ? "text" : "password"}
                  value={form.confirm_password}
                  onChange={onChange}
                  className={inputCls}
                  autoComplete="new-password"
                  disabled={isLoading}
                  placeholder="Re-enter new password"
                />
              </div>

              <p className="text-xs text-ds-text-muted">
                Password must be at least 6 characters. Avoid simple sequences
                like 123456.
              </p>

              <button
                type="submit"
                disabled={isLoading}
                className={`w-full h-11 rounded-lg text-white text-sm font-semibold transition focus:outline-none focus:ring-4 focus:ring-ds-action/20 ${
                  isLoading
                    ? "bg-ds-action/60 cursor-not-allowed"
                    : "bg-ds-action hover:bg-ds-action-hover"
                }`}
              >
                {isLoading ? "Saving..." : "Reset password"}
              </button>

              <Link
                href="/login"
                className="block text-center text-sm font-semibold text-ds-action hover:underline"
              >
                Back to login
              </Link>
            </form>
          )}
        </div>
      </div>
    </main>
  );
}
