"use client";

import Link from "next/link";
import { useState } from "react";
import { useForgotPassword } from "@/features/auth/hooks";
import { getApiErrorMessage } from "@/lib/apiErrors";
import ThemeController from "@/components/shared/others/ThemeController";

export default function ForgotPasswordPage() {
  const forgotMut = useForgotPassword();
  const [email, setEmail] = useState("");
  const [formError, setFormError] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");

  const isLoading = forgotMut.isPending;

  const onSubmit = async (e) => {
    e.preventDefault();
    setFormError("");

    const value = email.trim();
    if (!value) {
      setFormError("Please enter your email address.");
      return;
    }

    try {
      const res = await forgotMut.mutateAsync({ email: value });
      setSuccessMessage(
        res?.message ||
          "If an account exists for this email, password reset instructions have been sent.",
      );
      setSubmitted(true);
    } catch (err) {
      setFormError(getApiErrorMessage(err, "Could not process your request."));
    }
  };

  const labelCls =
    "block text-[12.5px] font-medium text-ds-text-secondary mb-1.5";
  const inputCls =
    "w-full h-11 rounded-lg border border-ds-border " +
    "bg-ds-surface-input px-3.5 text-sm text-ds-text-primary " +
    "placeholder:text-ds-text-muted " +
    "focus:outline-none focus:border-ds-action/50 focus:ring-4 focus:ring-ds-action/10 transition";

  return (
    <main className="min-h-screen bg-ds-page">
      <ThemeController />
      <div className="min-h-[80vh] flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-md rounded-2xl border border-ds-border bg-ds-surface p-6 md:p-8 shadow-sm">
          <h1 className="text-xl font-semibold text-ds-text-primary">
            Forgot password
          </h1>
          <p className="mt-1 text-sm text-ds-text-muted">
            Enter the email on your account. We will send reset instructions if
            it matches a JustClick user.
          </p>

          {submitted ? (
            <div className="mt-6 space-y-4">
              <div
                role="status"
                className="rounded-xl border border-ds-action/25 bg-ds-action/10 px-4 py-3 text-sm text-ds-text-primary"
              >
                {successMessage}
              </div>
              <Link
                href="/login"
                className="inline-flex h-11 w-full items-center justify-center rounded-lg bg-ds-action text-sm font-semibold text-white hover:bg-ds-action-hover transition"
              >
                Back to login
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
                <label className={labelCls} htmlFor="email">
                  Email <span className="text-ds-error">*</span>
                </label>
                <input
                  id="email"
                  name="email"
                  type="email"
                  value={email}
                  onChange={(e) => {
                    setFormError("");
                    setEmail(e.target.value);
                  }}
                  placeholder="you@university.edu"
                  className={inputCls}
                  autoComplete="email"
                  disabled={isLoading}
                />
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className={`w-full h-11 rounded-lg text-white text-sm font-semibold transition focus:outline-none focus:ring-4 focus:ring-ds-action/20 ${
                  isLoading
                    ? "bg-ds-action/60 cursor-not-allowed"
                    : "bg-ds-action hover:bg-ds-action-hover"
                }`}
              >
                {isLoading ? "Sending..." : "Send reset link"}
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
