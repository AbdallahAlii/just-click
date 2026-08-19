"use client";

import { useLogin } from "@/features/auth/hooks";
import { getApiErrorMessage } from "@/lib/apiErrors";
import { useSession } from "@/providers/SessionProvider";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import toast from "react-hot-toast";

const LoginForm = () => {
  const router = useRouter();
  const loginMut = useLogin();
  const { user } = useSession();

  const [form, setForm] = useState({
    username: "",
    password: "",
  });
  const [showPassword, setShowPassword] = useState(false);
  const [formError, setFormError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (user) router.replace("/materials");
  }, [user, router]);

  const onChange = (e) => {
    const { name, value } = e.target;
    setFormError("");
    setForm((p) => ({ ...p, [name]: value }));
  };

  const isFormValid = !!form.username.trim() && !!form.password.trim();
  const isBusy = isSubmitting || loginMut.isPending;
  const isSubmitDisabled = !isFormValid || isBusy;

  const onSubmit = async (e) => {
    e.preventDefault();
    setFormError("");

    if (isBusy) return;

    if (!form.username.trim() || !form.password.trim()) {
      const msg = "Please enter username and password.";
      setFormError(msg);
      toast.error(msg);
      return;
    }

    setIsSubmitting(true);

    try {
      await loginMut.mutateAsync({
        username: form.username.trim(),
        password: form.password,
      });

      toast.success("Login successful.");
      router.replace("/materials");
    } catch (e2) {
      const msg = getApiErrorMessage(e2, "Invalid username or password.");
      setFormError(msg);
      toast.error(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const labelCls =
    "block text-[12.5px] font-medium text-ds-text-secondary mb-1.5";

  const inputCls =
    "w-full min-w-0 h-11 rounded-lg border border-ds-border " +
    "bg-ds-surface-input px-3.5 text-sm text-ds-text-primary " +
    "placeholder:text-ds-text-muted " +
    "focus:outline-none focus:border-ds-action/50 focus:ring-4 focus:ring-ds-action/10 transition";

  return (
    <div className="w-full min-w-0">
      <div className="mb-5">
        <h2 className="text-xl font-semibold text-ds-text-primary">Sign in</h2>
        <p className="mt-1 text-sm text-ds-text-muted">
          New here?{" "}
          <Link
            href="/signup"
            className="font-semibold text-ds-action hover:underline"
          >
            Create account
          </Link>
        </p>
      </div>

      {formError ? (
        <div
          role="alert"
          className="mb-4 rounded-xl border border-ds-error/30 bg-ds-error/10 px-4 py-3 text-sm text-ds-error"
        >
          {formError}
        </div>
      ) : null}

      <form onSubmit={onSubmit} className="space-y-3.5">
        <div>
          <label className={labelCls} htmlFor="username">
            Username <span className="text-ds-error">*</span>
          </label>
          <input
            id="username"
            name="username"
            value={form.username}
            onChange={onChange}
            type="text"
            placeholder="Enter username"
            className={inputCls}
            autoComplete="username"
            disabled={isBusy}
          />
        </div>

        <div>
          <div className="flex items-center justify-between">
            <label className={labelCls} htmlFor="password">
              Password <span className="text-ds-error">*</span>
            </label>

            <button
              type="button"
              onClick={() => setShowPassword((v) => !v)}
              className="text-xs font-semibold text-ds-action hover:underline disabled:cursor-not-allowed"
              disabled={isBusy}
            >
              {showPassword ? "Hide" : "Show"}
            </button>
          </div>

          <input
            id="password"
            name="password"
            value={form.password}
            onChange={onChange}
            type={showPassword ? "text" : "password"}
            placeholder="Enter password"
            className={inputCls}
            autoComplete="current-password"
            disabled={isBusy}
          />
        </div>

        <div className="flex items-center justify-end pt-1">
          <Link
            href="/forgot-password"
            className="text-sm font-semibold text-ds-action hover:underline"
          >
            Forgot password?
          </Link>
        </div>

        <button
          type="submit"
          disabled={isSubmitDisabled}
          aria-disabled={isSubmitDisabled}
          aria-busy={isBusy}
          className={
            "mt-1 flex w-full min-h-11 shrink-0 items-center justify-center rounded-lg text-sm font-semibold " +
            "visible opacity-100 focus:outline-none focus:ring-4 focus:ring-ds-action/20 " +
            (isSubmitDisabled
              ? "cursor-not-allowed border border-ds-border bg-ds-surface-hover text-ds-text-muted"
              : "border border-transparent bg-ds-action text-white hover:bg-ds-action-hover")
          }
        >
          {isBusy ? "Signing in..." : "Sign in"}
        </button>
      </form>
    </div>
  );
};

export default LoginForm;
